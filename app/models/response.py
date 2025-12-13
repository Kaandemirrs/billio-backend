from pydantic import BaseModel
from typing import Optional, Any

class ApiResponse(BaseModel):
    """Standardize edilmiş API response"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[dict] = None

class ErrorDetail(BaseModel):
    """Error detayları"""
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[str] = None