from pydantic import BaseModel
from typing import List, Dict, Optional
from decimal import Decimal

# Response Models
class CategoryBreakdown(BaseModel):
    """Kategori bazında harcama"""
    entertainment: Optional[Decimal] = 0
    utilities: Optional[Decimal] = 0
    productivity: Optional[Decimal] = 0
    health: Optional[Decimal] = 0
    finance: Optional[Decimal] = 0
    education: Optional[Decimal] = 0
    other: Optional[Decimal] = 0

class CurrentMonthSummary(BaseModel):
    """Bu ay özeti"""
    total: Decimal
    currency: str
    subscription_count: int
    categories: Dict[str, Decimal]

class ComparisonData(BaseModel):
    """Karşılaştırma"""
    previous_month: Decimal
    difference: Decimal
    percentage_change: float
    trend: str  # up, down, stable

class YearlyProjection(BaseModel):
    """Yıllık projeksiyon"""
    total: Decimal
    average_monthly: Decimal

class TopSubscription(BaseModel):
    """En yüksek harcama"""
    name: str
    amount: Decimal
    percentage: float

class AnalyticsSummaryResponse(BaseModel):
    """Analytics summary response"""
    current_month: CurrentMonthSummary
    comparison: ComparisonData
    yearly_projection: YearlyProjection
    top_subscriptions: List[TopSubscription]

class MonthlyTrend(BaseModel):
    """Aylık trend"""
    month: str  # YYYY-MM
    total: Decimal
    subscription_count: int

class CategoryTrendData(BaseModel):
    """Kategori trend"""
    total: Decimal
    percentage: float
    trend: str  # up, down, stable
    change: float

class TrendsResponse(BaseModel):
    """Trends response"""
    monthly_trends: List[MonthlyTrend]
    category_breakdown: Dict[str, CategoryTrendData]