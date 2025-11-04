from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
import asyncio
import logging

from app.api.deps import get_current_user
from app.models.response import ApiResponse
from app.models.subscription import SubscriptionResponse
from app.services.google_search_service import google_search_service
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Request Models
class GetPriceRequest(BaseModel):
    """Fiyat bulucu isteği"""
    service_name: str = Field(..., min_length=1, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_name": "Netflix"
            }
        }

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

@router.post("/get-price", response_model=ApiResponse)
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

@router.post("/analyze-subscriptions", response_model=ApiResponse)
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
        
        # Her abonelik için Google'da indirim/kampanya ara (yalnızca predefined_bills dolu olanlar)
        search_tasks = []
        searched_subscriptions = []
        for subscription in request.subscriptions:
            if subscription.is_active:
                predefined_bills = getattr(subscription, "predefined_bills", None)
                if predefined_bills:
                    # display_name'i güvenli şekilde al
                    if isinstance(predefined_bills, dict):
                        display_name = predefined_bills.get("display_name")
                    else:
                        display_name = getattr(predefined_bills, "display_name", None)

                    if display_name and isinstance(display_name, str) and display_name.strip():
                        query = f"{display_name} Türkiye indirim kampanya promosyon kod"
                        search_tasks.append(google_search_service.search_google(query, num_results=3))
                        searched_subscriptions.append(subscription)
        
        # Paralel olarak tüm aramaları yap
        if search_tasks:
            search_results_list = await asyncio.gather(*search_tasks, return_exceptions=True)
        else:
            search_results_list = []
        
        # Tüm Google sonuçlarını birleştir
        context_parts = []
        
        for i, (subscription, search_results) in enumerate(zip(searched_subscriptions, search_results_list)):
            if isinstance(search_results, Exception):
                continue
                
            if search_results:
                # Label'ı display_name ile tercih et
                predefined_bills = getattr(subscription, "predefined_bills", None)
                if isinstance(predefined_bills, dict):
                    display_name = predefined_bills.get("display_name") or subscription.name
                else:
                    display_name = getattr(predefined_bills, "display_name", None) or subscription.name

                context_parts.append(f"\n{display_name} İNDİRİM BİLGİLERİ:")
                for j, result in enumerate(search_results, 1):
                    context_parts.append(f"  Kaynak {j}: {result.get('title', '')} - {result.get('snippet', '')}")
        
        context = "\n".join(context_parts) if context_parts else "İndirim bilgisi bulunamadı."
        # Debug Log 1: Google'dan Ne Geldi?
        print(f"GOOGLE_SEARCH SONUÇLARI: {context}")
        
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
        
        # Debug Log 2: AI'a Ne Gitti?
        print(f"GEMINI'YE GİDEN PROMPT: {gemini_prompt}")

        # Gemini'ye sor
        analysis = await gemini_service.ask_gemini(context=context, prompt=gemini_prompt)
        
        if not analysis:
            analysis = """
Aboneliklerinizi analiz ettim. İşte genel tasarruf önerilerim:

1. **Kullanmadığınız servisleri iptal edin**: Aylık {:.2f} TL harcamanızı gözden geçirin ve gerçekten kullandığınız servisleri belirleyin.

2. **Yıllık abonelik seçeneklerini değerlendirin**: Çoğu servis yıllık ödemede %15-20 indirim sunuyor.

3. **Aile planlarını araştırın**: Netflix, Spotify gibi servislerin aile planları kişi başı daha ekonomik olabilir.

Detaylı analiz için lütfen tekrar deneyin.
""".format(total_monthly)
        
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