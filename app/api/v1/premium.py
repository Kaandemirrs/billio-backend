from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from typing import Optional
from app.api.deps import get_current_user
from app.models.response import ApiResponse
from app.models.premium import (
    PurchaseRequest,
    VerifyPaymentRequest,
    CancelRequest
)
from app.services.premium_service import premium_service
from app.services.user_service import user_service

router = APIRouter()

@router.get("/premium/plans", response_model=ApiResponse)
async def get_plans():
    """
    Premium planları listele
    
    Authentication gerekmez, herkes görebilir
    
    Returns:
        Premium planlar (monthly, yearly, lifetime)
    """
    try:
        plans = premium_service.get_plans()
        
        return {
            "success": True,
            "data": {
                "plans": plans
            }
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

@router.get("/premium/features", response_model=ApiResponse)
async def get_features():
    """
    Premium özellikleri listele
    
    UI'da göstermek için
    
    Returns:
        Premium özellikler listesi
    """
    try:
        features = premium_service.get_features()
        
        return {
            "success": True,
            "data": {
                "features": features
            }
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

@router.get("/premium/status", response_model=ApiResponse)
async def get_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Kullanıcının premium durumunu kontrol et
    
    Returns:
        Premium/Free durum, özellikler, süre bilgileri
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
        
        # Status getir
        status_data = await premium_service.get_status(user_id)
        
        return {
            "success": True,
            "data": status_data
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

@router.post("/premium/purchase", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def purchase_premium(
    request: PurchaseRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Premium satın al
    
    - **plan_type**: monthly, yearly, lifetime
    - **payment_method**: stripe, iyzico, apple_pay, google_pay, mock
    - **payment_token**: Ödeme token'ı (mock mode için "mock_token")
    
    Mock Mode: payment_method="mock" ve payment_token="mock_token" kullanın
    
    Returns:
        Purchase bilgileri, transaction_id, süre
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
        
        # Satın al
        purchase = await premium_service.purchase(
            user_id=user_id,
            plan_type=request.plan_type,
            payment_method=request.payment_method,
            payment_token=request.payment_token
        )
        
        return {
            "success": True,
            "message": "Premium abonelik başarıyla satın alındı",
            "data": purchase
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "PAYMENT_FAILED",
                    "message": "Ödeme işlemi tamamlanamadı."
                }
            }
        )

@router.post("/premium/verify-payment", response_model=ApiResponse)
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Ödemeyi doğrula
    
    - **transaction_id**: Transaction ID
    - **payment_method**: Payment gateway
    
    Returns:
        Doğrulama sonucu
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
        
        # Doğrula
        result = await premium_service.verify_payment(
            user_id=user_id,
            transaction_id=request.transaction_id,
            payment_method=request.payment_method
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

@router.get("/premium/invoices", response_model=ApiResponse)
async def get_invoices(
    current_user: dict = Depends(get_current_user)
):
    """
    Fatura geçmişini listele
    
    Returns:
        Tüm satın alma faturaları, toplam harcama
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
        
        # Faturaları getir
        invoices = await premium_service.get_invoices(user_id)
        
        return {
            "success": True,
            "data": invoices
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

@router.post("/premium/cancel", response_model=ApiResponse)
async def cancel_premium(
    request: CancelRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Premium iptal et
    
    - **cancellation_reason**: İptal nedeni
    - **feedback**: Opsiyonel geri bildirim
    
    Returns:
        İptal bilgileri, erişim süresi
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
        
        # İptal et
        result = await premium_service.cancel(
            user_id=user_id,
            cancellation_reason=request.cancellation_reason,
            feedback=request.feedback
        )
        
        return {
            "success": True,
            "message": "Premium aboneliğiniz iptal edildi",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "CANCEL_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )

@router.post("/premium/reactivate", response_model=ApiResponse)
async def reactivate_premium(
    current_user: dict = Depends(get_current_user)
):
    """
    İptal edilen premium'u yeniden aktif et
    
    Returns:
        Yeniden aktif edilmiş premium bilgileri
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
        
        # Reactivate
        result = await premium_service.reactivate(user_id)
        
        return {
            "success": True,
            "message": "Premium aboneliğiniz yeniden aktif edildi",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "REACTIVATE_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )

@router.post("/premium/webhook/stripe", response_model=ApiResponse)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature")
):
    """
    Stripe webhook endpoint
    
    Raw body üzerinden imza doğrulaması yapılır.
    """
    try:
        payload = await request.body()
        result = await premium_service.process_webhook(
            webhook_type="stripe",
            raw_body=payload,
            signature=stripe_signature
        )
        return {
            "success": True,
            "data": result
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "WEBHOOK_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )

@router.post("/premium/webhook/iyzico", response_model=ApiResponse)
async def iyzico_webhook(
    request: Request,
    iyzico_signature: Optional[str] = Header(None, alias="Iyzico-Signature")
):
    """
    Iyzico webhook endpoint
    
    Raw body üzerinden imza doğrulaması yapılır.
    """
    try:
        payload = await request.body()
        result = await premium_service.process_webhook(
            webhook_type="iyzico",
            raw_body=payload,
            signature=iyzico_signature
        )
        return {
            "success": True,
            "data": result
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "WEBHOOK_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )
