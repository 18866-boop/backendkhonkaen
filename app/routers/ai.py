from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models import ComplaintCategory, AnalyticsLog
from ..schemas import AIPredictInput, AIPredictOutput, TopicModelingResponse
from ..security import get_current_user, admin_only, any_role, User as SecurityUser
from ..ai.classifier import classifier
from ..ai.predictor import predictor
from ..ai.topic_modeler import get_topic_modeling_data

router = APIRouter(prefix="/ai", tags=["AI Analytics & Models"])

@router.post("/predict", response_model=AIPredictOutput)
def predict_live(payload: AIPredictInput, db: Session = Depends(get_db), current_user: SecurityUser = Depends(any_role)):
    # Run NLP classifier on input text
    nlp_res = classifier.predict(payload.text)
    
    # Resolve category from db to get category ID
    db_cat = db.query(ComplaintCategory).filter(ComplaintCategory.name == nlp_res["category"]).first()
    category_id = db_cat.id if db_cat else 1
    
    # Run ML predictor
    # District ID defaulted to 1 (Downtown) for prediction preview
    ml_res = predictor.predict(
        category_id=category_id,
        district_id=1,
        urgency=nlp_res["urgency"]
    )
    
    return AIPredictOutput(
        category=nlp_res["category"],
        urgency=nlp_res["urgency"],
        confidence=nlp_res["confidence"],
        recommended_department=ml_res["recommended_department"],
        estimated_days=ml_res["estimated_days"],
        risk_level=ml_res["risk_level"],
        keywords=nlp_res["keywords"]
    )

@router.get("/topic-modeling", response_model=TopicModelingResponse)
def get_topic_modeling(db: Session = Depends(get_db), current_user: SecurityUser = Depends(any_role)):
    # Runs KMeans/PCA NLP modeling on complaints dataset
    try:
        data = get_topic_modeling_data(db)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Topic modeling error: {str(e)}")

@router.post("/retrain", status_code=status.HTTP_200_OK)
def retrain_models(db: Session = Depends(get_db), current_user: SecurityUser = Depends(admin_only)):
    # Retrain classifier (updates joblib model with any adjustments in training texts)
    # Retrain predictor (trains on completed database cases)
    try:
        classifier.train_models()
        predictor.train_on_db_data(db)
        
        # Log event
        db.add(AnalyticsLog(
            event_type="Model Retrained",
            description=f"AI Classification & Prediction Models were retrained successfully by Administrator '{current_user.username}'.",
            user_id=current_user.id
        ))
        db.commit()
        
        return {"status": "success", "message": "AI and Predictive models retrained successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retraining failed: {str(e)}"
        )
