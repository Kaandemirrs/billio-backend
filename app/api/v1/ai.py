from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import asyncio
import logging

from app.api.deps import get_current_user
from app.models.response import ApiResponse
from app.models.ai_analysis import (
    AnalyzeSuggestionRequest,
    FeedbackRequest
)
from app.models.subscription import SubscriptionResponse
from app.services.ai_service import ai_service
from app.services.user_service import user_service
from app.services.google_search_service import google_search_service
from app.services.gemini_service import gemini_service
from app.services.smart_price_service import smart_price_service

logger = logging.getLogger(__name__)

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

# New AI Models for RAG endpoints
class GetPriceRequest(BaseModel):
    """Fiyat bulucu isteği"""
    service_name: str = Field(..., min_length=1, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_name": "Netflix"
            }
        }


class SmartPriceRequest(BaseModel):
    service_name: str = Field(..., min_length=1, max_length=100)
    plan_name: str = Field("Standart Plan", min_length=1, max_length=100)

class AnalyzeSubscriptionsRequest(BaseModel):
    """Finansal analiz isteği"""
    subscriptions: List[SubscriptionResponse]
    
    class Config:
        json_schema_extra = {
            "example": {
                "subscriptions": [
                    {
                        "id": "1",
                        "name": "Netflix",
                        "category": "entertainment",
                        "amount": 149.99,
                        "currency": "TRY",
                        "billing_cycle": "monthly",
                        "billing_day": 15,
                        "start_date": "2025-01-01",
                        "next_payment_date": "2025-02-15",
                        "logo_url": None,
                        "color": "#E50914",
                        "is_active": True,
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00"
                    }
                ]
            }
        }

@router.post("/ai/get-price", response_model=ApiResponse)
async def get_price(
    request: GetPriceRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Servis fiyatı bulucu - Google Search + Gemini AI kullanarak güncel fiyat bilgisi
    
    Args:
        request: Servis adı içeren istek
        current_user: Giriş yapmış kullanıcı bilgisi
        
    Returns:
        Önerilen fiyat bilgisi
    """
    try:
        firebase_uid = current_user.get("uid")
        logger.info(f"Price search request from user {firebase_uid} for service: {request.service_name}")
        
        # Google Search sorgusu oluştur
        search_query = f"{request.service_name} Türkiye güncel fiyatı aylık abonelik"
        
        # Google'da ara
        google_results = await google_search_service.search_google(search_query, num_results=5)
        
        if not google_results:
            logger.warning(f"No Google search results found for: {search_query}")
            return {
                "success": True,
                "message": "Fiyat bilgisi bulunamadı",
                "data": {
                    "suggested_price": None,
                    "service_name": request.service_name,
                    "search_performed": True
                }
            }
        
        # Google sonuçlarını tek bir context'e birleştir
        context_parts = []
        for i, result in enumerate(google_results, 1):
            context_parts.append(f"Kaynak {i}: {result.get('title', '')} - {result.get('snippet', '')}")
        
        context = "\n".join(context_parts)
        
        # Gemini prompt'u oluştur
        gemini_prompt = f"""
BAĞLAM: {context}

GÖREV: Bu bağlamdan {request.service_name} için aylık standart plan fiyatını bul. 

KURALLAR:
1. Sadece Türkiye fiyatlarını dikkate al
2. Aylık abonelik fiyatını ara
3. Sadece sayısal değeri döndür (örn: 149.99)
4. Para birimi belirtme
5. Eğer net bir fiyat bulamazsan 'null' döndür
6. Birden fazla fiyat varsa en yaygın olanı seç

YANIT (sadece sayı veya null):
"""
        
        # Gemini'ye sor
        price_response = await gemini_service.ask_gemini(context=context, prompt=gemini_prompt)
        
        # Yanıtı işle
        suggested_price = None
        if price_response and price_response.strip().lower() != 'null':
            try:
                # Sayısal değeri çıkarmaya çalış
                price_str = price_response.strip().replace(',', '.')
                suggested_price = float(price_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse price from Gemini response: {price_response}")
        
        logger.info(f"Price search completed for {request.service_name}: {suggested_price}")
        
        return {
            "success": True,
            "message": "Fiyat araması tamamlandı",
            "data": {
                "suggested_price": suggested_price,
                "service_name": request.service_name,
                "search_performed": True,
                "sources_found": len(google_results)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_price: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "PRICE_SEARCH_ERROR",
                    "message": "Fiyat araması sırasında bir hata oluştu"
                }
            }
        )


@router.post("/ai/smart-price", response_model=ApiResponse)
async def get_smart_price_suggestion(
    request: SmartPriceRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        firebase_uid = current_user.get("uid")
        logger.info(
            f"Smart price request from user {firebase_uid} for service {request.service_name} plan {request.plan_name}"
        )

        result = await smart_price_service.find_price(
            service_name=request.service_name,
            plan_name=request.plan_name,
        )

        return {
            "success": True,
            "data": {
                "suggested_price": result.get("price"),
                "currency": result.get("currency"),
                "source": result.get("source"),
                "confidence": result.get("confidence"),
            },
        }
    except Exception as e:
        logger.error(f"Error in get_smart_price_suggestion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "SMART_PRICE_ERROR",
                    "message": "Akıllı fiyat araması sırasında bir hata oluştu",
                },
            },
        )

@router.post("/ai/analyze-subscriptions", response_model=ApiResponse)
async def analyze_subscriptions(
    request: AnalyzeSubscriptionsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Finansal analiz - Kullanıcının aboneliklerini analiz ederek tasarruf önerileri sunar
    
    Args:
        request: Kullanıcının abonelikleri
        current_user: Giriş yapmış kullanıcı bilgisi
        
    Returns:
        Finansal analiz ve tasarruf önerileri
    """
    try:
        firebase_uid = current_user.get("uid")
        logger.info(f"Subscription analysis request from user {firebase_uid} with {len(request.subscriptions)} subscriptions")
        
        if not request.subscriptions:
            return {
                "success": True,
                "message": "Analiz edilecek abonelik bulunamadı",
                "data": {
                    "analysis_text": "Henüz hiç aboneliğiniz yok. Abonelik eklediğinizde size özel tasarruf önerileri sunabilirim."
                }
            }
        
        # Her abonelik için Google'da indirim/kampanya ara
        search_tasks = []
        for subscription in request.subscriptions:
            if subscription.is_active:  # Sadece aktif abonelikler için ara
                query = f"{subscription.name} Türkiye indirim kampanya promosyon kod"
                search_tasks.append(google_search_service.search_google(query, num_results=3))
        
        # Paralel olarak tüm aramaları yap
        if search_tasks:
            search_results_list = await asyncio.gather(*search_tasks, return_exceptions=True)
        else:
            search_results_list = []
        
        # Tüm Google sonuçlarını birleştir
        context_parts = []
        active_subscriptions = [sub for sub in request.subscriptions if sub.is_active]
        
        for i, (subscription, search_results) in enumerate(zip(active_subscriptions, search_results_list)):
            if isinstance(search_results, Exception):
                continue
                
            if search_results:
                context_parts.append(f"\n{subscription.name} İNDİRİM BİLGİLERİ:")
                for j, result in enumerate(search_results, 1):
                    context_parts.append(f"  Kaynak {j}: {result.get('title', '')} - {result.get('snippet', '')}")
        
        context = "\n".join(context_parts) if context_parts else "İndirim bilgisi bulunamadı."
        
        # Kullanıcı verilerini özetle
        total_monthly = sum(float(sub.amount) for sub in request.subscriptions if sub.is_active and sub.billing_cycle == "monthly")
        total_yearly = sum(float(sub.amount) for sub in request.subscriptions if sub.is_active and sub.billing_cycle == "yearly")
        
        user_data_summary = f"""
KULLANICI ABONELİK ÖZETİ:
- Toplam aktif abonelik: {len([s for s in request.subscriptions if s.is_active])}
- Aylık toplam harcama: {total_monthly:.2f} TL
- Yıllık toplam harcama: {total_yearly:.2f} TL

ABONELİK DETAYLARI:
"""
        
        for sub in request.subscriptions:
            if sub.is_active:
                user_data_summary += f"- {sub.name}: {sub.amount} {sub.currency} ({sub.billing_cycle})\n"
        
        # Gemini prompt'u oluştur
        gemini_prompt = f"""
BAĞLAM (GÜNCEL İNDİRİM BİLGİLERİ): 
{context}

{user_data_summary}

GÖREV: Bu bağlamı ve kullanıcı verisini analiz et. Kullanıcıya güncel indirimlere göre 3 adet pratik tasarruf önerisi sun.

KURALLAR:
1. Türkçe yanıt ver
2. Somut ve uygulanabilir öneriler sun
3. Güncel indirim/kampanya bilgilerini kullan
4. Her öneri için tahmini tasarruf miktarı belirt
5. Kısa ve öz ol (maksimum 500 kelime)
6. Numaralı liste formatında yaz

YANIT:
"""
        
        # Gemini'ye sor
        analysis = await gemini_service.ask_gemini(context=context, prompt=gemini_prompt)
        
        if not analysis:
            analysis = f"""
Aboneliklerinizi analiz ettim. İşte genel tasarruf önerilerim:

1. **Kullanmadığınız servisleri iptal edin**: Aylık {total_monthly:.2f} TL harcamanızı gözden geçirin ve gerçekten kullandığınız servisleri belirleyin.

2. **Yıllık abonelik seçeneklerini değerlendirin**: Çoğu servis yıllık ödemede %15-20 indirim sunuyor.

3. **Aile planlarını araştırın**: Netflix, Spotify gibi servislerin aile planları kişi başı daha ekonomik olabilir.

Detaylı analiz için lütfen tekrar deneyin.
"""
        
        logger.info(f"Subscription analysis completed for user {firebase_uid}")
        
        return {
            "success": True,
            "message": "Finansal analiz tamamlandı",
            "data": {
                "analysis_text": analysis,
                "total_subscriptions": len(request.subscriptions),
                "active_subscriptions": len([s for s in request.subscriptions if s.is_active]),
                "monthly_total": total_monthly,
                "yearly_total": total_yearly
            }
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_subscriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "ANALYSIS_ERROR",
                    "message": "Finansal analiz sırasında bir hata oluştu"
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
