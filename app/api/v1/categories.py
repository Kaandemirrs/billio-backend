from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.api.deps import get_current_user
from app.models.response import ApiResponse
from app.services.category_service import category_service
from app.services.subscription_service import subscription_service
from app.services.user_service import user_service

router = APIRouter()

@router.get("/categories", response_model=ApiResponse)
async def get_categories(
    language: str = Query("tr", pattern="^(tr|en)$")
):
    """
    Kategorileri listele
    
    - **language**: Dil (tr, en)
    
    Authentication gerekmez, herkes görebilir
    
    Returns:
        Tüm kategoriler (icon, renk, açıklama ile)
    """
    try:
        categories = category_service.get_categories(language)
        
        return {
            "success": True,
            "data": {
                "categories": categories
            }
        }
        
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

@router.get("/categories/stats", response_model=ApiResponse)
async def get_category_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Kategori bazında istatistikler
    
    Kullanıcının aktif aboneliklerini kategorilere göre gruplar
    
    Returns:
        Kategori bazında abonelik sayısı, toplam harcama, yüzde
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
        
        # Stats al
        stats = await category_service.get_category_stats(
            user_id=user_id,
            subscription_service=subscription_service
        )
        
        return {
            "success": True,
            "data": stats
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