from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from app.api.deps import get_current_user
from app.models.response import ApiResponse
from app.models.notification import (
    TestNotificationRequest,
    ClearAllRequest
)
from app.services.notification_service import notification_service
from app.services.user_service import user_service
from app.services.notification_pusher_service import send_push_notification

router = APIRouter()

@router.get("/notifications", response_model=ApiResponse)
async def get_notifications(
    is_read: Optional[bool] = Query(None),
    type: Optional[str] = Query(None, pattern="^(payment_reminder|price_alert|savings_opportunity|system)$"),
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    current_user: dict = Depends(get_current_user)
):
    """
    Bildirimleri listele
    
    - **is_read**: Okunma filtresi (true/false/null=all)
    - **type**: Tip filtresi (payment_reminder, price_alert, etc.)
    - **limit**: Sayfa başına kayıt (1-100)
    - **page**: Sayfa numarası
    
    Returns:
        Bildirimler, okunmamış sayısı, pagination
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
        
        # Bildirimleri getir
        result = await notification_service.get_notifications(
            user_id=user_id,
            is_read=is_read,
            type=type,
            limit=limit,
            page=page
        )
        
        return {
            "success": True,
            "data": result
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

@router.get("/notifications/unread-count", response_model=ApiResponse)
async def get_unread_count(
    current_user: dict = Depends(get_current_user)
):
    """
    Okunmamış bildirim sayısı
    
    Mobil app badge için kullanılır
    
    Returns:
        Okunmamış bildirim sayısı
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
        
        # Sayıyı al
        unread_count = await notification_service.get_unread_count(user_id)
        
        return {
            "success": True,
            "data": {
                "unread_count": unread_count
            }
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

@router.get("/notifications/{notification_id}", response_model=ApiResponse)
async def get_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Tek bir bildirimi getir
    
    - **notification_id**: Bildirim ID
    
    Returns:
        Bildirim detayları
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
        
        # Bildirimi getir
        notification = await notification_service.get_notification_by_id(
            user_id=user_id,
            notification_id=notification_id
        )
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "NOTIFICATION_NOT_FOUND",
                        "message": "Bildirim bulunamadı"
                    }
                }
            )
        
        return {
            "success": True,
            "data": notification
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

@router.patch("/notifications/{notification_id}/read", response_model=ApiResponse)
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Bildirimi okundu olarak işaretle
    
    - **notification_id**: Bildirim ID
    
    Returns:
        Güncelleme onayı
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
        
        # Okundu işaretle
        result = await notification_service.mark_as_read(
            user_id=user_id,
            notification_id=notification_id
        )
        
        return {
            "success": True,
            "message": "Bildirim okundu olarak işaretlendi",
            "data": result
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

@router.post("/notifications/mark-all-read", response_model=ApiResponse)
async def mark_all_as_read(
    current_user: dict = Depends(get_current_user)
):
    """
    Tüm bildirimleri okundu olarak işaretle
    
    Returns:
        İşaretlenen bildirim sayısı
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
        
        # Tümünü okundu yap
        result = await notification_service.mark_all_as_read(user_id)
        
        return {
            "success": True,
            "message": "Tüm bildirimler okundu olarak işaretlendi",
            "data": result
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

@router.delete("/notifications/{notification_id}", response_model=ApiResponse)
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Bildirimi sil
    
    - **notification_id**: Bildirim ID
    
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
        
        # Sil
        success = await notification_service.delete_notification(
            user_id=user_id,
            notification_id=notification_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "NOTIFICATION_NOT_FOUND",
                        "message": "Bildirim bulunamadı"
                    }
                }
            )
        
        return {
            "success": True,
            "message": "Bildirim silindi",
            "data": {
                "id": notification_id,
                "deleted": True,
                "deleted_at": "2025-10-16T..."
            }
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

@router.delete("/notifications/clear-all", response_model=ApiResponse)
async def clear_all_notifications(
    request: Optional[ClearAllRequest] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Tüm bildirimleri temizle
    
    - **type**: (Opsiyonel) Sadece belirli tip bildirimler
    
    Returns:
        Silinen bildirim sayısı
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
        
        # Temizle
        type_filter = request.type if request else None
        result = await notification_service.clear_all_notifications(
            user_id=user_id,
            type=type_filter
        )
        
        return {
            "success": True,
            "message": "Bildirimler temizlendi",
            "data": result
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

@router.post("/notifications/test", response_model=ApiResponse)
async def create_test_notification(
    request: TestNotificationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Test bildirimi oluştur (Development)
    
    - **type**: Bildirim tipi
    - **title**: Başlık
    - **message**: Mesaj
    - **action_type**: (Opsiyonel) Aksiyon tipi
    - **action_data**: (Opsiyonel) Aksiyon datası
    
    Returns:
        Oluşturulan test bildirimi
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
        
        # Test bildirimi oluştur
        notification = await notification_service.create_test_notification(
            user_id=user_id,
            type=request.type,
            title=request.title,
            message=request.message,
            action_type=request.action_type,
            action_data=request.action_data
        )

        # Cihaz push bildirimi gönder (varsa)
        try:
            fcm_token = await user_service.get_fcm_token_by_user_id(user_id)
            if fcm_token:
                await send_push_notification(fcm_token, request.title, request.message)
        except Exception:
            # Push gönderimi başarısız olsa bile API akışını bozma
            pass
        
        return {
            "success": True,
            "message": "Test bildirimi oluşturuldu",
            "data": notification
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