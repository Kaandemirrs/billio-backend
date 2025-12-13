from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# Enums / sabitler
CATEGORIES = [
    "entertainment",
    "utilities",
    "productivity",
    "health",
    "finance",
    "education",
    "other",
]
CURRENCIES = ["TRY", "USD", "EUR"]


# -----------------------------
# Service Models
# -----------------------------
class ServiceBase(BaseModel):
    """Service ortak alanlar (create/update için temel)."""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., pattern="^(entertainment|utilities|productivity|health|finance|education|other)$")
    logo_url: Optional[str] = None
    primary_color: str = Field(default="#6366f1", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field(default="#ffffff", pattern=r"^#[0-9A-Fa-f]{6}$")
    is_popular: bool = False
    keywords: Optional[List[str]] = None


class ServiceCreate(ServiceBase):
    """Yeni service oluşturma modeli."""
    class Config:
        json_schema_extra = {
            "example": {
                "name": "netflix",
                "display_name": "Netflix",
                "category": "entertainment",
                "logo_url": "https://logo.clearbit.com/netflix.com",
                "primary_color": "#e50914",
                "secondary_color": "#ffffff",
                "is_popular": True,
                "keywords": ["netflix", "dizi", "film"],
            }
        }


class Service(BaseModel):
    """Service DB satırı (read)."""
    id: str
    name: str
    display_name: str
    category: str
    logo_url: Optional[str]
    primary_color: str
    secondary_color: str
    is_popular: bool
    keywords: Optional[List[str]]
    created_at: datetime
    updated_at: datetime


class ServiceReadBasic(Service):
    """Sadece service bilgilerini içeren optimize read modeli."""
    pass


class ServiceReadWithPlans(Service):
    """Service bilgileri + temel plan bilgileri (optimize)."""
    service_plans: Optional[List["ServicePlanReadBasic"]] = None


# -----------------------------
# Service Plan Models
# -----------------------------
class ServicePlanBase(BaseModel):
    """ServicePlan ortak alanlar (create/update için temel)."""
    service_id: str = Field(..., min_length=1)
    plan_name: str = Field(..., min_length=1, max_length=100)
    plan_identifier: str = Field(..., min_length=1, max_length=100)
    cached_price: Optional[Decimal] = None
    currency: Optional[str] = Field(default=None, pattern="^(TRY|USD|EUR)$")
    last_updated_ai: Optional[datetime] = None
    is_active: bool = True


class ServicePlanCreate(ServicePlanBase):
    """Yeni plan oluşturma modeli."""
    class Config:
        json_schema_extra = {
            "example": {
                "service_id": "c6e0a6a2-4a3d-4d2a-b208-6b66f8fd8c7f",
                "plan_name": "Standard",
                "plan_identifier": "netflix-standard-tr",
                "cached_price": 149.99,
                "currency": "TRY",
                "last_updated_ai": "2025-01-01T12:00:00Z",
                "is_active": True,
            }
        }


class ServicePlan(BaseModel):
    """ServicePlan DB satırı (read)."""
    id: str
    service_id: str
    plan_name: str
    plan_identifier: str
    cached_price: Optional[Decimal]
    currency: Optional[str]
    last_updated_ai: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServicePlanReadBasic(ServicePlan):
    """Sadece plan bilgilerini içeren optimize read modeli."""
    pass


class ServicePlanRead(ServicePlan):
    """ServicePlan read modeli (geri ilişki alanı dahil edilebilir)."""
    # Back relationship temsilî (SQLModel yokken optional bırakıyoruz)
    service: Optional[Service] = None


# İleri referansların çözülmesi için
ServiceReadBasic.model_rebuild()
ServiceReadWithPlans.model_rebuild()
ServicePlanReadBasic.model_rebuild()
ServicePlanRead.model_rebuild()

# Geriye dönük uyumluluk için alias
ServiceRead = ServiceReadWithPlans