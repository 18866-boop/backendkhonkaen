from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel

from .data_loader import data_loader

class ComplaintCreate(BaseModel):
    title: str
    type: str
    department: str
    sub_department: str
    district: str
    community: str

app = FastAPI(
    title="Khon Kaen Smart City Complaint Analytics API",
    description="API for analyzing civic complaint data in Khon Kaen Municipality",
    version="1.0.0",
    docs_url="/docs"
)

# CORS configuration to allow local frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/summary")
def get_summary():
    return data_loader.get_summary()

@app.get("/api/by-type")
def get_by_type():
    return data_loader.get_by_type()

@app.get("/api/by-department")
def get_by_department():
    return data_loader.get_by_department()

@app.get("/api/performance")
def get_performance():
    return data_loader.get_performance()

@app.get("/api/by-district")
def get_by_district():
    return data_loader.get_by_district()

@app.get("/api/by-status")
def get_by_status():
    return data_loader.get_by_status()

@app.get("/api/monthly-trend")
def get_monthly_trend():
    return data_loader.get_monthly_trend()

@app.get("/api/top-keywords")
def get_top_keywords(limit: int = 20):
    return data_loader.get_keywords(limit)

@app.get("/api/records")
def get_records(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str = Query("", description="Search term for complaint text or id"),
    type: str = Query("", description="Filter by complaint type"),
    district: str = Query("", description="Filter by district")
):
    return data_loader.get_records(
        page=page,
        per_page=per_page,
        search=search,
        complaint_type=type,
        district=district
    )

@app.post("/api/complaints")
def create_complaint(complaint: ComplaintCreate):
    new_id = data_loader.add_complaint(
        title=complaint.title,
        complaint_type=complaint.type,
        department=complaint.department,
        sub_department=complaint.sub_department,
        district=complaint.district,
        community=complaint.community
    )
    return {"status": "success", "id": new_id, "message": "คำร้องได้รับการบันทึกเรียบร้อยแล้ว"}

@app.put("/api/complaints/{complaint_id}/resolve")
def resolve_complaint(complaint_id: str):
    try:
        data_loader.resolve_complaint(complaint_id)
        return {"status": "success", "message": f"คำร้องหมายเลข {complaint_id} ได้รับการแก้ไขและบันทึกเสร็จสิ้นแล้ว"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app_name": "Khon Kaen Smart City Complaint Analytics",
        "api_docs": "/docs",
        "version": "1.0.0"
    }
