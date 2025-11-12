from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models.services import ServicePlanReadBasic

# Enums
CATEGORIES = ["entertainment", "utilities", "productivity", "health", "finance", "education", "other"]
CURRENCIES = ["TRY", "USD", "EUR"]
BILLING_CYCLES = ["daily", "weekly", "monthly", "yearly"]

# Request Models
class CreateSubscriptionRequest(BaseModel):
    """Yeni abonelik oluştur"""
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(...)
    amount: Decimal = Field(..., ge=0.01)
    currency: str = Field(default="TRY")
    billing_cycle: str = Field(...)
    billing_day: int = Field(..., ge=1, le=31)
    start_date: date
    service_plan_id: Optional[str] = None
    logo_url: Optional[str] = None
    color: Optional[str] = Field(default="#6366f1", pattern="^#[0-9A-Fa-f]{6}$")
    
    @validator('category')
    def validate_category(cls, v):
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}")
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        if v not in CURRENCIES:
            raise ValueError(f"currency must be one of {CURRENCIES}")
        return v
    
    @validator('billing_cycle')
    def validate_billing_cycle(cls, v):
        if v not in BILLING_CYCLES:
            raise ValueError(f"billing_cycle must be one of {BILLING_CYCLES}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Netflix",
                "category": "entertainment",
                "amount": 149.99,
                "currency": "TRY",
                "billing_cycle": "monthly",
                "billing_day": 15,
                "start_date": "2025-10-15",
                "logo_url": "https://cdn.billio.app/logos/netflix.png",
                "color": "#E50914"
            }
        }

class UpdateSubscriptionRequest(BaseModel):
    """Abonelik güncelle"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = None
    amount: Optional[Decimal] = Field(..., ge=0.01)
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    billing_day: Optional[int] = Field(None, ge=1, le=31)
    start_date: Optional[date] = None
    service_plan_id: Optional[str] = None
    logo_url: Optional[str] = None
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    
    @validator('category')
    def validate_category(cls, v):
        if v is not None and v not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}")
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        if v is not None and v not in CURRENCIES:
            raise ValueError(f"currency must be one of {CURRENCIES}")
        return v
    
    @validator('billing_cycle')
    def validate_billing_cycle(cls, v):
        if v is not None and v not in BILLING_CYCLES:
            raise ValueError(f"billing_cycle must be one of {BILLING_CYCLES}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 159.99,
                "billing_day": 10
            }
        }

class ToggleSubscriptionRequest(BaseModel):
    """Abonelik durumu değiştir"""
    is_active: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_active": False
            }
        }

# Response Models
class SubscriptionResponse(BaseModel):
    """Subscription response"""
    id: str
    name: str
    category: str
    amount: Decimal
    currency: str
    billing_cycle: str
    billing_day: int
    start_date: date
    next_payment_date: Optional[date]
    service_plan_id: Optional[str] = None
    # service_plans JOIN'den gelen embed objeyi yakala
    service_plans: Optional[ServicePlanReadBasic] = Field(None, alias="service_plans")
    # Akıllı Backend: Zam uyarısı durumu
    price_alert_status: str = "none"
    logo_url: Optional[str]
    color: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class SubscriptionSummary(BaseModel):
    """Abonelik özeti"""
    total_monthly: Decimal
    total_yearly: Decimal
    active_count: int
    inactive_count: int
    currency: str

class PaginationInfo(BaseModel):
    """Pagination bilgisi"""
    page: int
    limit: int
    total_pages: int
    total_items: int

class SubscriptionListResponse(BaseModel):
    """Abonelik listesi response"""
    subscriptions: List[SubscriptionResponse]
    summary: SubscriptionSummary
    pagination: PaginationInfo