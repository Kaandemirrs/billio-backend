from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_current_user
from app.models.response import ApiResponse
from app.services.user_service import user_service
from app.models.user import (
    UpdateProfileRequest, 
    DeleteAccountRequest,
    RequestPhoneVerificationRequest,  # Yeni
    VerifyPhoneRequest,  # Yeni
    UpdateSettingsRequest,
    RegisterDeviceRequest
)
router = APIRouter()

@router.get("/user/profile", response_model=ApiResponse)
async def get_profile(
    current_user: dict = Depends(get_current_user)
):
    """
    Kullanıcı profilini getir
    
    Token'dan firebase_uid alınarak Supabase'den user bilgileri getirilir
    
    Returns:
        User profil bilgileri
    """
    try:
        firebase_uid = current_user.get("uid")
        
        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Token'da uid bulunamadı"
                    }
                }
            )
        
        # User'ı getir
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
        
        return {
            "success": True,
            "data": user
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
    

@router.put("/user/profile", response_model=ApiResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Profil bilgilerini güncelle
    
    - **full_name**: Yeni isim (opsiyonel)
    - **phone_number**: Yeni telefon (opsiyonel)
    
    Not: Telefon numarası değişirse phone_verified otomatik false olur
    
    Returns:
        Güncellenmiş user bilgileri
    """
    try:
        firebase_uid = current_user.get("uid")
        
        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Token'da uid bulunamadı"
                    }
                }
            )
        
        # Telefon numarası formatı kontrol et
        if request.phone_number:
            if not request.phone_number.startswith("+90") or len(request.phone_number) != 13:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INVALID_PHONE",
                            "message": "Telefon numarası +90 ile başlamalı ve 13 karakter olmalı",
                            "field": "phone_number"
                        }
                    }
                )
        
        # Profili güncelle
        updated_user = await user_service.update_profile(
            firebase_uid=firebase_uid,
            full_name=request.full_name,
            phone_number=request.phone_number
        )
        
        if not updated_user:
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
        
        return {
            "success": True,
            "message": "Profil güncellendi",
            "data": updated_user
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
    """
    Profil bilgilerini güncelle
    
    - **full_name**: Yeni isim (opsiyonel)
    - **phone_number**: Yeni telefon (opsiyonel)
    
    Not: Telefon numarası değişirse phone_verified otomatik false olur
    
    Returns:
        Güncellenmiş user bilgileri
    """
    try:
        firebase_uid = current_user.get("uid")
        
        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Token'da uid bulunamadı"
                    }
                }
            )
        
        # Telefon numarası formatı kontrol et
        if request.phone_number:
            # +90 ile başlamalı ve 13 karakter olmalı
            if not request.phone_number.startswith("+90") or len(request.phone_number) != 13:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INVALID_PHONE",
                            "message": "Telefon numarası +90 ile başlamalı ve 13 karakter olmalı",
                            "field": "phone_number"
                        }
                    }
                )
        
        # Profili güncelle
        updated_user = await user_service.update_profile(
            firebase_uid=firebase_uid,
            full_name=request.full_name,
            phone_number=request.phone_number
        )
        
        if not updated_user:
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
        
        return {
            "success": True,
            "message": "Profil güncellendi",
            "data": updated_user
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

@router.delete("/user/account", response_model=ApiResponse)
async def delete_account(
    request: DeleteAccountRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Hesabı tamamen sil (KVKK uyumlu)
    
    - **confirmation**: "DELETE_MY_ACCOUNT" yazmalısınız
    
    CASCADE DELETE: Tüm subscriptions, ai_analysis, notifications, premium_purchases silinir
    
    Returns:
        Silme onayı
    """
    try:
        firebase_uid = current_user.get("uid")
        
        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Token'da uid bulunamadı"
                    }
                }
            )
        
        # Confirmation kontrol et
        if request.confirmation != "DELETE_MY_ACCOUNT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_CONFIRMATION",
                        "message": "Confirmation 'DELETE_MY_ACCOUNT' olmalı",
                        "field": "confirmation"
                    }
                }
            )
        
        # Hesabı sil
        success = await user_service.delete_account(firebase_uid)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": {
                        "code": "DELETE_FAILED",
                        "message": "Hesap silinemedi"
                    }
                }
            )
        
        return {
            "success": True,
            "message": "Hesabınız ve tüm verileriniz kalıcı olarak silindi"
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
    

@router.post("/user/phone/request-verification", response_model=ApiResponse)
async def request_phone_verification(
    request: RequestPhoneVerificationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    SMS doğrulama kodu gönder
    
    - **phone_number**: Doğrulanacak telefon numarası
    
    6 haneli kod üretilir ve SMS gönderilir (5 dakika geçerli)
    
    Returns:
        Kod bilgileri
    """
    try:
        firebase_uid = current_user.get("uid")
        
        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Token'da uid bulunamadı"
                    }
                }
            )
        
        # Telefon formatı kontrol et
        if not request.phone_number.startswith("+90") or len(request.phone_number) != 13:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_PHONE",
                        "message": "Telefon numarası +90 ile başlamalı ve 13 karakter olmalı",
                        "field": "phone_number"
                    }
                }
            )
        
        # Doğrulama kodu gönder
        await user_service.request_phone_verification(
            firebase_uid=firebase_uid,
            phone_number=request.phone_number
        )
        
        return {
            "success": True,
            "message": "Doğrulama kodu gönderildi",
            "data": None
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

@router.post("/user/phone/verify", response_model=ApiResponse)
async def verify_phone(
    request: VerifyPhoneRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    SMS kodunu doğrula
    
    - **verification_code**: 6 haneli SMS kodu
    
    Kod doğruysa phone_verified = true olur
    
    Returns:
        Doğrulama sonucu
    """
    try:
        firebase_uid = current_user.get("uid")
        
        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Token'da uid bulunamadı"
                    }
                }
            )
        
        # Kodu doğrula
        success = await user_service.verify_phone(
            firebase_uid=firebase_uid,
            verification_code=request.verification_code
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "VERIFICATION_FAILED",
                        "message": "Doğrulama başarısız"
                    }
                }
            )
        
        return {
            "success": True,
            "message": "Telefon numarası başarıyla doğrulandı"
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "VERIFICATION_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )    
    
@router.get("/user/settings", response_model=ApiResponse)
async def get_settings(
    current_user: dict = Depends(get_current_user)
):
    """
    Kullanıcı ayarlarını getir
    
    Returns:
        User settings
    """
    try:
        firebase_uid = current_user.get("uid")
        
        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Token'da uid bulunamadı"
                    }
                }
            )
        
        # Settings'i getir
        settings = await user_service.get_settings(firebase_uid)
        
        return {
            "success": True,
            "data": settings
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

@router.put("/user/settings", response_model=ApiResponse)
async def update_settings(
    request: UpdateSettingsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Kullanıcı ayarlarını güncelle
    
    - **preferred_currency**: TRY, USD, EUR
    - **preferred_language**: tr, en
    - **notification_enabled**: true, false
    - **reminder_days**: 1-30
    - **theme**: light, dark, auto
    
    Returns:
        Güncellenmiş settings
    """
    try:
        firebase_uid = current_user.get("uid")
        
        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Token'da uid bulunamadı"
                    }
                }
            )
        
        # Settings'i güncelle
        updated_settings = await user_service.update_settings(
            firebase_uid=firebase_uid,
            preferred_currency=request.preferred_currency,
            preferred_language=request.preferred_language,
            notification_enabled=request.notification_enabled,
            reminder_days=request.reminder_days,
            theme=request.theme
        )
        
        return {
            "success": True,
            "message": "Ayarlar güncellendi",
            "data": updated_settings
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

@router.post("/user/register-device", response_model=ApiResponse)
async def register_device(
    request: RegisterDeviceRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Cihaz FCM token'ını kaydet
    
    Body: { fcm_token: string }
    """
    try:
        firebase_uid = current_user.get("uid")
        
        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Token'da uid bulunamadı"
                    }
                }
            )

        result = await user_service.update_fcm_token(
            firebase_uid=firebase_uid,
            fcm_token=request.fcm_token
        )

        return {
            "success": True,
            "message": "FCM token güncellendi",
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
