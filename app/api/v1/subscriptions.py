from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.api.deps import get_current_user
from app.models.response import ApiResponse
from app.models.subscription import (
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
    ToggleSubscriptionRequest
)
from app.services.subscription_service import subscription_service
from app.services.user_service import user_service
from typing import Optional

router = APIRouter()

@router.get("/subscriptions", response_model=ApiResponse)
async def get_subscriptions(
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: str = Query("created_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Tüm abonelikleri listele
    
    - **category**: Kategori filtresi (entertainment, utilities, etc.)
    - **is_active**: Aktiflik filtresi (true/false)
    - **sort_by**: Sıralama alanı (amount, created_at, name)
    - **order**: Sıralama yönü (asc/desc)
    - **page**: Sayfa numarası
    - **limit**: Sayfa başına kayıt (max 100)
    
    Returns:
        Subscriptions, summary, pagination
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
        
        # Subscriptions listele
        result = await subscription_service.get_subscriptions(
            user_id=user_id,
            category=category,
            is_active=is_active,
            sort_by=sort_by,
            order=order,
            page=page,
            limit=limit
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )

@router.get("/subscriptions/{subscription_id}", response_model=ApiResponse)
async def get_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Tek bir aboneliği detaylı getir
    
    Returns:
        Subscription detayları
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
        
        # Subscription getir
        subscription = await subscription_service.get_subscription_by_id(
            subscription_id=subscription_id,
            user_id=user_id
        )
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "SUBSCRIPTION_NOT_FOUND",
                        "message": "Abonelik bulunamadı"
                    }
                }
            )
        
        return {
            "success": True,
            "data": subscription
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )

@router.post("/subscriptions", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Yeni abonelik ekle
    
    Returns:
        Oluşturulan subscription
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
        
        # Subscription oluştur
        subscription = await subscription_service.create_subscription(
            user_id=user_id,
            subscription_data=request.dict(exclude_none=True)
        )
        
        return {
            "success": True,
            "message": "Abonelik başarıyla eklendi",
            "data": subscription
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )

@router.put("/subscriptions/{subscription_id}", response_model=ApiResponse)
async def update_subscription(
    subscription_id: str,
    request: UpdateSubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Abonelik güncelle
    
    Returns:
        Güncellenmiş subscription
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
        
        # Subscription güncelle
        updated_subscription = await subscription_service.update_subscription(
            subscription_id=subscription_id,
            user_id=user_id,
            update_data=request.dict(exclude_none=True)
        )
        
        if not updated_subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "SUBSCRIPTION_NOT_FOUND",
                        "message": "Abonelik bulunamadı"
                    }
                }
            )
        
        return {
            "success": True,
            "message": "Abonelik güncellendi",
            "data": updated_subscription
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )

@router.delete("/subscriptions/{subscription_id}", response_model=ApiResponse)
async def delete_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Aboneliği sil
    
    Returns:
        Silme onayı
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
        
        # Subscription sil
        success = await subscription_service.delete_subscription(
            subscription_id=subscription_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "SUBSCRIPTION_NOT_FOUND",
                        "message": "Abonelik bulunamadı"
                    }
                }
            )
        
        return {
            "success": True,
            "message": "Abonelik silindi",
            "data": {
                "id": subscription_id,
                "deleted": True
            }
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )

@router.patch("/subscriptions/{subscription_id}/toggle", response_model=ApiResponse)
async def toggle_subscription(
    subscription_id: str,
    request: ToggleSubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Aboneliği aktif/pasif yap
    
    Returns:
        Güncellenmiş subscription
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
        
        # Toggle
        updated_subscription = await subscription_service.toggle_subscription(
            subscription_id=subscription_id,
            user_id=user_id,
            is_active=request.is_active
        )
        
        if not updated_subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "SUBSCRIPTION_NOT_FOUND",
                        "message": "Abonelik bulunamadı"
                    }
                }
            )
        
        return {
            "success": True,
            "message": "Abonelik durumu güncellendi",
            "data": updated_subscription
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )
