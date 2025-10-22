from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal

# Request Models
class AnalyzeSuggestionRequest(BaseModel):
    """Öneri uygula request"""
    action: str = Field(..., pattern="^apply$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "apply"
            }
        }

class FeedbackRequest(BaseModel):
    """Geri bildirim request"""
    feedback: str = Field(..., pattern="^(helpful|not_helpful|wrong)$")
    comment: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "feedback": "helpful",
                "comment": "Çok doğru bir öneri, teşekkürler!"
            }
        }

# Response Models
class Suggestion(BaseModel):
    """AI önerisi"""
    type: str  # downgrade, alternative, cancel, keep
    suggested_plan: Optional[str] = None
    suggested_amount: Optional[Decimal] = None
    alternative_service: Optional[str] = None
    potential_monthly_savings: Optional[Decimal] = None
    potential_yearly_savings: Optional[Decimal] = None
    confidence_score: float
    reason: str

class AnalysisDetails(BaseModel):
    """Analiz detayları"""
    usage_pattern: str
    recommendation: str
    priority: Optional[str] = None

class AnalysisResponse(BaseModel):
    """Analiz response"""
    id: str
    subscription_id: str
    current_plan: str
    current_amount: Decimal
    suggestions: List[Suggestion]
    analysis_details: AnalysisDetails
    created_at: datetime

class BulkRecommendation(BaseModel):
    """Toplu analiz önerisi"""
    subscription_id: str
    subscription_name: str
    action: str  # keep, downgrade, cancel, alternative
    potential_savings: Optional[Decimal] = None
    priority: Optional[str] = None
    reason: Optional[str] = None

class BulkAnalysisResponse(BaseModel):
    """Toplu analiz response"""
    total_analyzed: int
    analysis_id: str
    total_potential_savings: Dict[str, Decimal]
    recommendations: List[BulkRecommendation]
    summary: Dict[str, int]
    created_at: datetime

class ApplySuggestionResponse(BaseModel):
    """Öneri uygulama response"""
    analysis_id: str
    subscription_id: str
    old_amount: Decimal
    new_amount: Decimal
    monthly_savings: Decimal
    is_applied: bool
    applied_at: datetime

class FeedbackResponse(BaseModel):
    """Geri bildirim response"""
    analysis_id: str
    user_feedback: str
    feedback_at: datetime

class HistoryItem(BaseModel):
    """Geçmiş analiz item"""
    id: str
    subscription_name: str
    suggestion_type: str
    potential_savings: Optional[Decimal]
    is_applied: bool
    applied_at: Optional[datetime]
    user_feedback: Optional[str]
    created_at: datetime

class HistorySummary(BaseModel):
    """Geçmiş özet"""
    total_analyses: int
    applied_count: int
    total_savings_realized: Decimal
    currency: str

class StatsResponse(BaseModel):
    """AI kullanım istatistikleri"""
    total_analyses: int
    applied_suggestions: int
    total_savings: Decimal
    average_confidence: float
    feedback_distribution: Dict[str, int]