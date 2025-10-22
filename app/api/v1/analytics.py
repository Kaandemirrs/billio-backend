from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.api.deps import get_current_user
from app.models.response import ApiResponse
from app.services.analytics_service import analytics_service
from app.services.user_service import user_service

router = APIRouter()

@router.get("/analytics/summary", response_model=ApiResponse)
async def get_summary(
    period: str = Query("monthly", pattern="^(monthly|yearly)$"),
    currency: str = Query("TRY", pattern="^(TRY|USD|EUR)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Genel harcama özeti
    
    - **period**: Dönem (monthly, yearly)
    - **currency**: Para birimi (TRY, USD, EUR)
    
    Returns:
        Bu ay özeti, karşılaştırma, projeksiyon, top subscriptions
    """
    try:
        firebase_uid = current_user.get("uid")
        
        # User ID al
        user = await user_service.get_user_by_firebase_uid(firebase_uid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "USER_NOT_FOUND",
                        "message": "Kullanıcı bulunamadı"
                    }
                }
            )
        
        user_id = user.get("id")
        
        # Summary al
        summary = await analytics_service.get_summary(
            user_id=user_id,
            period=period,
            currency=currency
        )
        
        return {
            "success": True,
            "data": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
        )

@router.get("/analytics/trends", response_model=ApiResponse)
async def get_trends(
    months: int = Query(12, ge=1, le=24),
    current_user: dict = Depends(get_current_user)
):
    """
    Harcama trendleri (son N ay)
    
    - **months**: Kaç ay geriye (1-24)
    
    Returns:
        Aylık trendler, kategori breakdown
    """
    try:
        firebase_uid = current_user.get("uid")
        
        # User ID al
        user = await user_service.get_user_by_firebase_uid(firebase_uid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "USER_NOT_FOUND",
                        "message": "Kullanıcı bulunamadı"
                    }
                }
            )
        
        user_id = user.get("id")
        
        # Trends al
        trends = await analytics_service.get_trends(
            user_id=user_id,
            months=months
        )
        
        return {
            "success": True,
            "data": trends
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
        )