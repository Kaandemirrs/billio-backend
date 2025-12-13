from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

class Category(BaseModel):
    """Kategori"""
    id: str
    name: str
    name_en: str
    icon: str
    color: str
    description: str

class CategoryStats(BaseModel):
    """Kategori istatistikleri"""
    id: str
    name: str
    subscription_count: int
    total_monthly: Decimal
    percentage: float