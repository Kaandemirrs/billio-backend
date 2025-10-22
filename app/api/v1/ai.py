from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional 
from app.api.deps import get_current_user
from app.models.response import ApiResponse
from app.models.ai_analysis import (
    AnalyzeSuggestionRequest,
    FeedbackRequest
)
from app.services.ai_service import ai_service
from app.services.user_service import user_service

router = APIRouter()

@router.post("/ai/analyze/{subscription_id}", response_model=ApiResponse)
async def analyze_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Tek bir aboneliği AI ile analiz et
    
    - **subscription_id**: Analiz edilecek abonelik ID
    
    Returns:
        AI analiz sonucu, öneriler, tasarruf potansiyeli
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
        
        # AI Analizi yap
        analysis = await ai_service.analyze_subscription(
            user_id=user_id,
            subscription_id=subscription_id
        )
        
        return {
            "success": True,
            "data": analysis
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

@router.get("/ai/analyze/{subscription_id}", response_model=ApiResponse)
async def get_subscription_analysis(
    subscription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Aboneliğin son analizini getir
    
    - **subscription_id**: Abonelik ID
    
    Returns:
        Son AI analizi (varsa)
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
        
        # Son analizi getir
        analysis = await ai_service.get_latest_analysis(
            user_id=user_id,
            subscription_id=subscription_id
        )
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "ANALYSIS_NOT_FOUND",
                        "message": "Bu abonelik için analiz bulunamadı"
                    }
                }
            )
        
        return {
            "success": True,
            "data": analysis
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

@router.post("/ai/bulk-analyze", response_model=ApiResponse)
async def bulk_analyze(
    current_user: dict = Depends(get_current_user)
):
    """
    Tüm abonelikleri toplu analiz et
    
    Returns:
        Toplu analiz sonuçları, toplam tasarruf, öneriler
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
        
        # Bulk analiz
        result = await ai_service.bulk_analyze(user_id=user_id)
        
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

@router.post("/ai/apply-suggestion/{analysis_id}", response_model=ApiResponse)
async def apply_suggestion(
    analysis_id: str,
    request: AnalyzeSuggestionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    AI önerisini uygula (abonelik miktarını güncelle)
    
    - **analysis_id**: Analiz ID
    - **action**: "apply" (öneriyi uygula)
    
    Returns:
        Uygulama sonucu, eski/yeni miktar, tasarruf
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
        
        # Öneriyi uygula
        result = await ai_service.apply_suggestion(
            user_id=user_id,
            analysis_id=analysis_id
        )
        
        return {
            "success": True,
            "message": "Öneri uygulandı",
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
                    "code": "APPLICATION_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )

@router.post("/ai/feedback/{analysis_id}", response_model=ApiResponse)
async def add_feedback(
    analysis_id: str,
    request: FeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    AI analizine geri bildirim ver
    
    - **analysis_id**: Analiz ID
    - **feedback**: helpful, not_helpful, wrong
    - **comment**: Opsiyonel yorum
    
    Returns:
        Geri bildirim onayı
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
        
        # Feedback ekle
        result = await ai_service.add_feedback(
            user_id=user_id,
            analysis_id=analysis_id,
            feedback=request.feedback,
            comment=request.comment
        )
        
        return {
            "success": True,
            "message": "Geri bildiriminiz kaydedildi",
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
                    "code": "FEEDBACK_ERROR",
                    "message": "İşlem tamamlanamadı."
                }
            }
        )

@router.get("/ai/history", response_model=ApiResponse)
async def get_history(
    is_applied: Optional[bool] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    current_user: dict = Depends(get_current_user)
):
    """
    Geçmiş AI analizlerini listele
    
    - **is_applied**: Uygulanmış analizler (true/false/null=all)
    - **limit**: Sayfa başına kayıt (1-100)
    - **page**: Sayfa numarası
    
    Returns:
        Geçmiş analizler, özet, pagination
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
        
        # History getir
        history = await ai_service.get_history(
            user_id=user_id,
            is_applied=is_applied,
            limit=limit,
            page=page
        )
        
        return {
            "success": True,
            "data": history
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

@router.delete("/ai/history/{analysis_id}", response_model=ApiResponse)
async def delete_analysis(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Analizi sil
    
    - **analysis_id**: Silinecek analiz ID
    
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
        success = await ai_service.delete_analysis(
            user_id=user_id,
            analysis_id=analysis_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "ANALYSIS_NOT_FOUND",
                        "message": "Analiz bulunamadı"
                    }
                }
            )
        
        return {
            "success": True,
            "message": "Analiz silindi",
            "data": {
                "id": analysis_id,
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

@router.get("/ai/stats", response_model=ApiResponse)
async def get_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    AI kullanım istatistikleri
    
    Returns:
        Toplam analiz, uygulanan öneri, toplam tasarruf, feedback dağılımı
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
        stats = await ai_service.get_stats(user_id=user_id)
        
        return {
            "success": True,
            "data": stats
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
