from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="Viewer")  # Admin, Officer, Viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    complaints_created = relationship("Complaint", back_populates="creator", foreign_keys="Complaint.created_by_id")
    complaints_assigned = relationship("Complaint", back_populates="assignee", foreign_keys="Complaint.assigned_to_id")
    logs = relationship("AnalyticsLog", back_populates="user")

class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    population = Column(Integer, default=50000)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    risk_score = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    complaints = relationship("Complaint", back_populates="district")

class ComplaintCategory(Base):
    __tablename__ = "complaint_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    complaints = relationship("Complaint", back_populates="category")

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("complaint_categories.id"), nullable=False)
    status = Column(String, default="Pending")  # Pending, In Progress, Completed, Rejected
    urgency = Column(String, default="Medium")  # Low, Medium, High
    risk_level = Column(String, default="Low")  # Low, Medium, High, Critical
    recommended_department = Column(String, nullable=True)
    estimated_completion_days = Column(Float, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="complaints_created", foreign_keys=[created_by_id])
    assignee = relationship("User", back_populates="complaints_assigned", foreign_keys=[assigned_to_id])
    district = relationship("District", back_populates="complaints")
    category = relationship("ComplaintCategory", back_populates="complaints")
    ai_prediction = relationship("AIPrediction", back_populates="complaint", uselist=False, cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="complaint", cascade="all, delete-orphan")

class AIPrediction(Base):
    __tablename__ = "ai_predictions"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, unique=True)
    predicted_category = Column(String, nullable=False)
    predicted_urgency = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    risk_level = Column(String, default="Low")
    completion_days = Column(Float, nullable=True)
    keywords = Column(Text, nullable=True)  # Comma-separated
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    complaint = relationship("Complaint", back_populates="ai_prediction")

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    complaint = relationship("Complaint", back_populates="attachments")

class AnalyticsLog(Base):
    __tablename__ = "analytics_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)  # User login, Complaint Created, Status Changed, Model Retrained
    description = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="logs")
