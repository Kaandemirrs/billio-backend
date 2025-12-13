from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

# Enums
NOTIFICATION_TYPES = ["payment_reminder", "price_alert", "savings_opportunity", "system"]
ACTION_TYPES = ["open_subscription", "open_analysis", "open_url"]

# Request Models
class TestNotificationRequest(BaseModel):
    """Test bildirimi oluştur"""
    type: str = Field(..., pattern="^(payment_reminder|price_alert|savings_opportunity|system)$")
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=500)
    action_type: Optional[str] = Field(None, pattern="^(open_subscription|open_analysis|open_url)$")
    action_data: Optional[Dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "payment_reminder",
                "title": "Test Bildirimi",
                "message": "Bu bir test bildirimidir"
            }
        }

class ClearAllRequest(BaseModel):
    """Tümünü temizle request"""
    type: Optional[str] = Field(None, pattern="^(payment_reminder|price_alert|savings_opportunity|system)$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "payment_reminder"
            }
        }

# Response Models
class NotificationResponse(BaseModel):
    """Notification response"""
    id: str
    type: str
    title: str
    message: str
    action_type: Optional[str]
    action_data: Optional[Dict]
    scheduled_for: Optional[datetime]
    sent_at: Optional[datetime]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

class NotificationListResponse(BaseModel):
    """Notification liste response"""
    notifications: List[NotificationResponse]
    unread_count: int
    pagination: Dict

class UnreadCountResponse(BaseModel):
    """Okunmamış sayısı"""
    unread_count: int

class MarkReadResponse(BaseModel):
    """Okundu response"""
    id: str
    is_read: bool
    read_at: datetime

class MarkAllReadResponse(BaseModel):
    """Tümü okundu response"""
    marked_count: int
    marked_at: datetime

class DeleteResponse(BaseModel):
    """Silme response"""
    id: str
    deleted: bool
    deleted_at: datetime

class ClearAllResponse(BaseModel):
    """Tümünü temizle response"""
    deleted_count: int
    deleted_at: datetime