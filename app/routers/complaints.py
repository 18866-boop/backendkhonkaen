from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import uuid
from datetime import datetime

from ..database import get_db
from ..models import Complaint, ComplaintCategory, District, AIPrediction, Attachment, AnalyticsLog, User
from ..schemas import ComplaintCreate, ComplaintResponse, ComplaintDetailResponse, ComplaintUpdate, ComplaintCategoryResponse, DistrictResponse, AttachmentResponse, AnalyticsLogResponse
from ..security import get_current_user, officer_or_admin, any_role, User as SecurityUser
from ..ai.classifier import classifier
from ..ai.predictor import predictor
from ..config import settings

router = APIRouter(prefix="/complaints", tags=["Complaints"])

@router.get("/categories", response_model=List[ComplaintCategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(ComplaintCategory).all()

@router.get("/districts", response_model=List[DistrictResponse])
def get_districts(db: Session = Depends(get_db)):
    return db.query(District).all()

@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def create_complaint(
    complaint_in: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: SecurityUser = Depends(get_current_user)
):
    # Check category and district exist
    category = db.query(ComplaintCategory).filter(ComplaintCategory.id == complaint_in.category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Invalid Category ID")
        
    district = db.query(District).filter(District.id == complaint_in.district_id).first()
    if not district:
        raise HTTPException(status_code=400, detail="Invalid District ID")

    # 1. Run AI NLP text classification (Category, Urgency, Keywords)
    nlp_results = classifier.predict(complaint_in.description)
    
    # 2. Run Predictive ML Model (Est completion days, Risk Level, Recommended Dept)
    ml_results = predictor.predict(
        category_id=complaint_in.category_id,
        district_id=complaint_in.district_id,
        urgency=nlp_results["urgency"]
    )
    
    # Create the Complaint object
    db_complaint = Complaint(
        title=complaint_in.title,
        description=complaint_in.description,
        district_id=complaint_in.district_id,
        category_id=complaint_in.category_id,
        status="Pending",
        urgency=nlp_results["urgency"],
        risk_level=ml_results["risk_level"],
        recommended_department=ml_results["recommended_department"],
        estimated_completion_days=ml_results["estimated_days"],
        latitude=complaint_in.latitude,
        longitude=complaint_in.longitude,
        created_by_id=current_user.id
    )
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    
    # Create AI Prediction record
    db_prediction = AIPrediction(
        complaint_id=db_complaint.id,
        predicted_category=nlp_results["category"],
        predicted_urgency=nlp_results["urgency"],
        confidence_score=nlp_results["confidence"],
        risk_level=ml_results["risk_level"],
        completion_days=ml_results["estimated_days"],
        keywords=",".join(nlp_results["keywords"])
    )
    db.add(db_prediction)
    
    # Log the action
    db.add(AnalyticsLog(
        event_type="Complaint Created",
        description=f"Complaint #{db_complaint.id} ('{db_complaint.title}') submitted by {current_user.username}. AI classified as '{nlp_results['category']}' with {int(nlp_results['confidence']*100)}% confidence.",
        user_id=current_user.id
    ))
    db.commit()
    db.refresh(db_complaint)
    
    return db_complaint

@router.get("/", response_model=List[ComplaintResponse])
def get_complaints(
    search: Optional[str] = None,
    status: Optional[str] = None,
    category_id: Optional[int] = None,
    district_id: Optional[int] = None,
    urgency: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_desc: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: SecurityUser = Depends(get_current_user)
):
    query = db.query(Complaint)
    
    # Apply filters
    if status:
        query = query.filter(Complaint.status == status)
    if category_id:
        query = query.filter(Complaint.category_id == category_id)
    if district_id:
        query = query.filter(Complaint.district_id == district_id)
    if urgency:
        query = query.filter(Complaint.urgency == urgency)
        
    if search:
        query = query.filter(
            (Complaint.title.ilike(f"%{search}%")) | 
            (Complaint.description.ilike(f"%{search}%"))
        )
        
    # Apply sorting
    if sort_by == "created_at":
        order_col = Complaint.created_at
    elif sort_by == "urgency":
        order_col = Complaint.urgency
    elif sort_by == "status":
        order_col = Complaint.status
    else:
        order_col = Complaint.created_at
        
    if sort_desc:
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())
        
    return query.offset(skip).limit(limit).all()

@router.get("/{id}", response_model=ComplaintDetailResponse)
def get_complaint(
    id: int,
    db: Session = Depends(get_db),
    current_user: SecurityUser = Depends(get_current_user)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@router.put("/{id}", response_model=ComplaintResponse)
def update_complaint(
    id: int,
    complaint_update: ComplaintUpdate,
    db: Session = Depends(get_db),
    current_user: SecurityUser = Depends(officer_or_admin)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    update_data = complaint_update.dict(exclude_unset=True)
    
    # Validate assigned officer
    if "assigned_to_id" in update_data and update_data["assigned_to_id"] is not None:
        assignee = db.query(User).filter(User.id == update_data["assigned_to_id"]).first()
        if not assignee or assignee.role not in ["Officer", "Admin"]:
            raise HTTPException(status_code=400, detail="Assigned user must be an Officer or Admin")

    old_status = complaint.status
    old_assignee_id = complaint.assigned_to_id

    for key, value in update_data.items():
        setattr(complaint, key, value)
        
    db.commit()
    db.refresh(complaint)

    # Log changes
    logs_to_add = []
    if "status" in update_data and update_data["status"] != old_status:
        logs_to_add.append(AnalyticsLog(
            event_type="Status Changed",
            description=f"Complaint #{complaint.id} status changed from '{old_status}' to '{complaint.status}' by user '{current_user.username}'.",
            user_id=current_user.id
        ))
        
    if "assigned_to_id" in update_data and update_data["assigned_to_id"] != old_assignee_id:
        assignee_name = db.query(User).filter(User.id == complaint.assigned_to_id).first().username if complaint.assigned_to_id else "Unassigned"
        logs_to_add.append(AnalyticsLog(
            event_type="Complaint Assigned",
            description=f"Complaint #{complaint.id} assigned to '{assignee_name}' by user '{current_user.username}'.",
            user_id=current_user.id
        ))

    for log in logs_to_add:
        db.add(log)
    db.commit()
    
    return complaint

@router.post("/{id}/attachments", response_model=AttachmentResponse)
def upload_attachment(
    id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: SecurityUser = Depends(get_current_user)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Validate file size and type
    allowed_mime_types = ["image/jpeg", "image/png", "image/gif", "application/pdf"]
    if file.content_type not in allowed_mime_types:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, GIF, and PDF uploads are allowed")

    # Generate unique file name
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    dest_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    # Save file
    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Get file size
    file_size = os.path.getsize(dest_path)

    # Save to database
    db_attachment = Attachment(
        complaint_id=complaint.id,
        filename=file.filename,
        file_path=dest_path,
        mime_type=file.content_type,
        file_size=file_size
    )
    db.add(db_attachment)
    
    # Log action
    db.add(AnalyticsLog(
        event_type="Attachment Uploaded",
        description=f"File '{file.filename}' uploaded to Complaint #{complaint.id} by {current_user.username}.",
        user_id=current_user.id
    ))
    db.commit()
    db.refresh(db_attachment)
    
    return db_attachment

@router.get("/{id}/logs", response_model=List[AnalyticsLogResponse])
def get_complaint_logs(
    id: int,
    db: Session = Depends(get_db),
    current_user: SecurityUser = Depends(any_role)
):
    # Return audit logs mentioning this complaint ID in the description
    logs = db.query(AnalyticsLog).filter(
        AnalyticsLog.description.like(f"%Complaint #{id}%")
    ).order_by(AnalyticsLog.timestamp.desc()).all()
    return logs
