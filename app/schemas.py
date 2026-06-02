from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

# District Schemas
class DistrictResponse(BaseModel):
    id: int
    name: str
    population: int
    latitude: float
    longitude: float
    risk_score: float

    class Config:
        from_attributes = True

# Category Schemas
class ComplaintCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

# Attachment Schemas
class AttachmentResponse(BaseModel):
    id: int
    complaint_id: int
    filename: str
    file_path: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# AI Prediction Schemas
class AIPredictionResponse(BaseModel):
    id: int
    complaint_id: int
    predicted_category: str
    predicted_urgency: str
    confidence_score: float
    risk_level: str
    completion_days: Optional[float] = None
    keywords: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Complaint Schemas
class ComplaintBase(BaseModel):
    title: str
    description: str
    district_id: int
    category_id: int
    latitude: float
    longitude: float

class ComplaintCreate(ComplaintBase):
    pass

class ComplaintResponse(BaseModel):
    id: int
    title: str
    description: str
    district_id: int
    category_id: int
    status: str
    urgency: str
    risk_level: str
    recommended_department: Optional[str] = None
    estimated_completion_days: Optional[float] = None
    latitude: float
    longitude: float
    created_by_id: int
    assigned_to_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Detailed Complaint response including related objects
class ComplaintDetailResponse(ComplaintResponse):
    creator: UserResponse
    assignee: Optional[UserResponse] = None
    district: DistrictResponse
    category: ComplaintCategoryResponse
    ai_prediction: Optional[AIPredictionResponse] = None
    attachments: List[AttachmentResponse] = []

    class Config:
        from_attributes = True

class ComplaintUpdate(BaseModel):
    status: Optional[str] = None
    urgency: Optional[str] = None
    assigned_to_id: Optional[int] = None

# Analytics Log Schemas
class AnalyticsLogResponse(BaseModel):
    id: int
    event_type: str
    description: str
    user_id: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True

# Dashboard Stats Schemas
class KPIStats(BaseModel):
    total_complaints: int
    pending_complaints: int
    in_progress_complaints: int
    completed_complaints: int
    resolution_rate: float
    sla_breaches: int

class CategoryCount(BaseModel):
    category: str
    count: int

class DistrictCount(BaseModel):
    district: str
    count: int
    latitude: float
    longitude: float

class DailyTrend(BaseModel):
    date: str
    count: int

class DashboardStatsResponse(BaseModel):
    kpis: KPIStats
    categories_distribution: List[CategoryCount]
    districts_distribution: List[DistrictCount]
    recent_complaints: List[ComplaintResponse]
    daily_trends: List[DailyTrend]

# Performance Analytics Stats Schemas
class ResolutionTimeByDistrict(BaseModel):
    district: str
    avg_days: float

class StaffWorkload(BaseModel):
    staff_name: str
    username: str
    assigned_count: int
    completed_count: int
    avg_resolution_days: float

class AnalyticsStatsResponse(BaseModel):
    kpis: KPIStats
    monthly_trends: List[DailyTrend]  # month-by-month list
    resolution_time_by_district: List[ResolutionTimeByDistrict]
    staff_performance: List[StaffWorkload]
    category_resolution_rate: List[CategoryCount]  # average days per category

# Topic Modeling Schemas
class TopicClusterPoint(BaseModel):
    x: float
    y: float
    label: str
    category: str
    complaint_id: int
    title: str

class TopicModelingResponse(BaseModel):
    word_cloud: List[dict]  # text: frequency items
    clusters: List[TopicClusterPoint]
    top_keywords: List[str]
    trending_topics: List[dict]

# AI live prediction input and output
class AIPredictInput(BaseModel):
    text: str

class AIPredictOutput(BaseModel):
    category: str
    urgency: str
    confidence: float
    recommended_department: str
    estimated_days: float
    risk_level: str
    keywords: List[str]
