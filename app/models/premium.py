from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal

# Enums
PLAN_TYPES = ["monthly", "yearly", "lifetime"]
PAYMENT_METHODS = ["stripe", "iyzico", "apple_pay", "google_pay", "mock"]
PURCHASE_STATUS = ["active", "expired", "cancelled", "refunded"]

# Request Models
class PurchaseRequest(BaseModel):
    """Premium satın alma request"""
    plan_type: str = Field(..., pattern="^(monthly|yearly|lifetime)$")
    payment_method: str = Field(..., pattern="^(stripe|iyzico|apple_pay|google_pay|mock)$")
    payment_token: str = Field(..., min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_type": "yearly",
                "payment_method": "mock",
                "payment_token": "mock_token_test123"
            }
        }

class VerifyPaymentRequest(BaseModel):
    """Ödeme doğrulama request"""
    transaction_id: str = Field(..., min_length=1)
    payment_method: str = Field(..., pattern="^(stripe|iyzico|apple_pay|google_pay)$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "stripe_txn_123456",
                "payment_method": "stripe"
            }
        }

class CancelRequest(BaseModel):
    """Premium iptal request"""
    cancellation_reason: str = Field(..., pattern="^(too_expensive|not_using|missing_features|found_alternative|other)$")
    feedback: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "cancellation_reason": "too_expensive",
                "feedback": "Daha uygun fiyat olursa tekrar alırım"
            }
        }

class WebhookRequest(BaseModel):
    """Webhook request (Stripe/Iyzico'dan gelecek)"""
    event_type: str
    data: Dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "payment.succeeded",
                "data": {
                    "transaction_id": "stripe_txn_123",
                    "amount": 399.99
                }
            }
        }

# Response Models
class PremiumFeature(BaseModel):
    """Premium özellik"""
    id: str
    name: str
    description: str
    icon: Optional[str]

class PremiumPlan(BaseModel):
    """Premium plan"""
    id: str
    name: str
    description: str
    price: Decimal
    original_price: Optional[Decimal]
    currency: str
    billing_cycle: str
    savings: Optional[str]
    features: List[str]
    popular: bool

class PremiumStatus(BaseModel):
    """Premium durum (Premium user)"""
    is_premium: bool
    plan_type: str
    starts_at: Optional[datetime]
    expires_at: Optional[datetime]
    days_remaining: Optional[int]
    auto_renewal: bool
    features: List[str]
    usage_stats: Optional[Dict]

class FreeStatus(BaseModel):
    """Free user durumu"""
    is_premium: bool
    plan_type: str
    features: List[str]
    limitations: Dict
    upgrade_benefits: List[str]

class PurchaseResponse(BaseModel):
    """Satın alma response"""
    purchase_id: str
    plan_type: str
    amount: Decimal
    currency: str
    payment_method: str
    transaction_id: str
    starts_at: datetime
    expires_at: datetime
    status: str
    invoice_url: Optional[str]
    created_at: datetime

class Invoice(BaseModel):
    """Fatura"""
    id: str
    purchase_id: str
    plan_type: str
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    invoice_url: Optional[str]
    created_at: datetime

class InvoicesResponse(BaseModel):
    """Faturalar response"""
    invoices: List[Invoice]
    total_spent: Decimal
    currency: str

class CancelResponse(BaseModel):
    """İptal response"""
    cancelled_at: datetime
    access_until: datetime
    refund_eligible: bool
    refund_policy: str

class ReactivateResponse(BaseModel):
    """Yeniden aktif response"""
    plan_type: str
    auto_renewal: bool
    expires_at: datetime
    reactivated_at: datetime