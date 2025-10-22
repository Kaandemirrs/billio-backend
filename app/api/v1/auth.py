from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_current_user
from app.models.auth import SyncUserRequest, SyncUserResponse
from app.models.response import ApiResponse
from app.services.auth_service import auth_service

router = APIRouter()

@router.post("/auth/sync-user", response_model=ApiResponse)
async def sync_user(
    request: SyncUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Firebase'den gelen user'ı Supabase'e senkronize et
    
    - **firebase_uid**: Token'dan otomatik alınır
    - **email**: Token'dan otomatik alınır
    - **full_name**: Opsiyonel, request body'den
    
    Returns:
        User bilgileri ve is_new_user flag
    """
    try:
        # Token'dan gelen bilgiler
        firebase_uid = current_user.get("uid")
        email = current_user.get("email")
        
        if not firebase_uid or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Token'da uid veya email bulunamadı"
                    }
                }
            )
        
        # User'ı senkronize et
        result = await auth_service.sync_user(
            firebase_uid=firebase_uid,
            email=email,
            full_name=request.full_name
        )
        
        message = "Yeni kullanıcı oluşturuldu" if result["is_new_user"] else "Kullanıcı senkronize edildi"
        
        return {
            "success": True,
            "message": message,
            "data": result
        }
        
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
