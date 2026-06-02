import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Complaint Analytics Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-jwt-auth-1234567890-abcdef")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Defaults to local SQLite, but can be overridden with a PostgreSQL URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./complaints.db")
    
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    
    class Config:
        case_sensitive = True

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
