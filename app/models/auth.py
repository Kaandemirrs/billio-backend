from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Request Models
class SyncUserRequest(BaseModel):
    """Sync user request body"""
    full_name: Optional[str] = None

class UserSettingsResponse(BaseModel):
    """User settings response"""
    preferred_currency: str
    preferred_language: str
    notification_enabled: bool
    reminder_days: int
    theme: str

class UserResponse(BaseModel):
    """User response model"""
    id: str
    firebase_uid: str
    email: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    phone_verified: bool
    subscription_type: str
    premium_expires_at: Optional[datetime] = None
    settings: UserSettingsResponse
    created_at: datetime
    last_login_at: Optional[datetime] = None

class SyncUserResponse(BaseModel):
    """Sync user response"""
    user: UserResponse
    is_new_user: bool