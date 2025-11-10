from pydantic import BaseModel, Field
from typing import Optional
import re

class UpdateProfileRequest(BaseModel):
    """Update profile request"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Ahmet Yılmaz",
                "phone_number": "+905551234567"
            }
        }

class DeleteAccountRequest(BaseModel):
    """Delete account request"""
    confirmation: str = Field(..., description="DELETE_MY_ACCOUNT yazmalısınız")
    
    class Config:
        json_schema_extra = {
            "example": {
                "confirmation": "DELETE_MY_ACCOUNT"
            }
        }
        

class RequestPhoneVerificationRequest(BaseModel):
    """Request phone verification"""
    phone_number: str = Field(..., min_length=13, max_length=13)
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "+905551234567"
            }
        }

class VerifyPhoneRequest(BaseModel):
    """Verify phone code"""
    verification_code: str = Field(..., min_length=6, max_length=6)
    
    class Config:
        json_schema_extra = {
            "example": {
                "verification_code": "123456"
            }
        }        

class UpdateSettingsRequest(BaseModel):
    """Update settings request"""
    preferred_currency: Optional[str] = Field(None, pattern="^(TRY|USD|EUR)$")
    preferred_language: Optional[str] = Field(None, pattern="^(tr|en)$")
    notification_enabled: Optional[bool] = None
    reminder_days: Optional[int] = Field(None, ge=1, le=30)
    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "preferred_currency": "USD",
                "preferred_language": "en",
                "notification_enabled": False,
                "reminder_days": 7,
                "theme": "dark"
            }
        }

class RegisterDeviceRequest(BaseModel):
    """Register device token request"""
    fcm_token: str = Field(..., min_length=10)
    
    class Config:
        json_schema_extra = {
            "example": {
                "fcm_token": "fcm_token_example_abcdef123456"
            }
        }