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
from app.services.analysis_context_service import analysis_context_service
from app.services.subscription_service import subscription_service
from app.services.user_service import user_service
from app.services.notification_service import notification_service
from app.services.notification_pusher_service import send_push_notification

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
                "message": "Fiyat araması tamamlandı",
                "data": {
                    "price_analysis_text": "Güncel fiyat bilgisi bulunamadı.",
                    "service_name": request.service_name,
                    "search_performed": True,
                    "sources_found": 0
                }
            }
        
        # Google sonuçlarını tek bir context'e birleştir
        context_parts = []
        for i, result in enumerate(google_results, 1):
            context_parts.append(f"Kaynak {i}: {result.get('title', '')} - {result.get('snippet', '')}")
        
        context = "\n".join(context_parts)
        # Debug Log: Google'dan Ne Geldi?
        print(f"GOOGLE_SEARCH SONUÇLARI: {context}")
        
        # Gemini prompt'u oluştur
        gemini_prompt = (
            f"BAĞLAM: {context}\n"
            f"GÖREV: Sadece yukarıdaki BAĞLAM metnini kullanarak, '{request.service_name}' için 'Bireysel', 'Standart' veya 'en ucuz ücretli' planların"
            " fiyatlarını özetleyen BİR PARAGRAFLIK kısa bir 'yazı' (analiz metni) yaz. Kullanıcıya hangi planın ne kadar olduğunu söyle."
            " (Örn: 'AI, Netflix'in Standart planını 149.99 TL olarak buldu...')."
            " BAĞLAM içinde net bir fiyat bulamazsan, 'Güncel fiyat bilgisi bulunamadı.' döndür."
        )
        # Debug Log: AI'a Ne Gitti?
        print(f"GEMINI'YE GİDEN PROMPT: {gemini_prompt}")
        
        # Gemini'ye sor
        price_response = await gemini_service.ask_gemini(context=context, prompt=gemini_prompt)
        
        # Yanıtı işle (özet metin)
        price_analysis_text = None
        if price_response:
            text = price_response.strip()
            price_analysis_text = text if text else None
        
        logger.info(f"Price search completed for {request.service_name}")
        
        return {
            "success": True,
            "message": "Fiyat araması tamamlandı",
            "data": {
                "price_analysis_text": price_analysis_text or "Güncel fiyat bilgisi bulunamadı.",
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
        
        # Her "Premium" marka (predefined_bills dolu olanlar) için birden fazla Google sorgusu çalıştır
        search_tasks = []
        tasks_meta = []  # Her görev için (subscription, display_name, sorgu_türü) bilgisini tutar
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
                        # Genişletilmiş sorgular
                        queries = [
                            (f"{display_name} güncel fiyatları", "güncel fiyatları"),
                            (f"{display_name} öğrenci planı", "öğrenci planı"),
                            (f"{display_name} aile planı", "aile planı"),
                        ]

                        for q, label in queries:
                            search_tasks.append(google_search_service.search_google(q, num_results=3))
                            tasks_meta.append({
                                "subscription": subscription,
                                "display_name": display_name,
                                "label": label,
                            })
        
        # Paralel olarak tüm aramaları yap
        if search_tasks:
            search_results_list = await asyncio.gather(*search_tasks, return_exceptions=True)
        else:
            search_results_list = []
        
        # Tüm Google sonuçlarını birleştir
        context_parts = []
        # Sonuçları marka bazında grupla
        grouped_results = {}
        for meta, results in zip(tasks_meta, search_results_list):
            if isinstance(results, Exception) or not results:
                continue
            sub_id = getattr(meta["subscription"], "id", None) or id(meta["subscription"])  # güvenli key
            if sub_id not in grouped_results:
                grouped_results[sub_id] = {
                    "display_name": meta["display_name"] or meta["subscription"].name,
                    "groups": []
                }
            grouped_results[sub_id]["groups"].append({
                "label": meta["label"],
                "results": results
            })

        # Grupları bağlama dönüştür
        for brand in grouped_results.values():
            context_parts.append(f"\n{brand['display_name']} BİLGİLER:")
            for group in brand["groups"]:
                context_parts.append(f"  {group['label'].upper()}:")
                for j, result in enumerate(group["results"], 1):
                    context_parts.append(
                        f"    Kaynak {j}: {result.get('title', '')} - {result.get('snippet', '')}"
                    )
        
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

        # Bildirimi oluştur ve push gönder (savings_opportunity)
        try:
            # User ID al
            user = await user_service.get_user_by_firebase_uid(firebase_uid)
            if user and user.get("id"):
                user_id = user.get("id")
                title = "Yeni bir tasarruf önerisi bulduk!"
                # Mesajı çok uzun olmaması için kısalt
                message = (analysis or "Tasarruf önerisi bulundu.")
                message = message.strip()
                if len(message) > 200:
                    message = message[:197] + "..."

                # Notifications tablosuna INSERT
                await notification_service.create_test_notification(
                    user_id=user_id,
                    type="savings_opportunity",
                    title=title,
                    message=message,
                    action_type=None,
                    action_data=None
                )

                # FCM token'ı çek ve push gönder
                try:
                    fcm_token = await user_service.get_fcm_token_by_user_id(user_id)
                    if fcm_token:
                        await send_push_notification(fcm_token, title, message)
                except Exception:
                    # Push gönderimi başarısız olsa bile akışı bozma
                    pass
        except Exception:
            # Bildirim/push hataları ana akışı bozmasın
            pass

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

@router.post("/analysis", response_model=ApiResponse)
async def analysis(
    current_user: dict = Depends(get_current_user)
):
    """
    RAG destekli finansal analiz – indirim ve tasarruf odaklı 10 maddelik rapor üretir.

    İç bağlam: Kullanıcının aktif abonelikleri + AI’ın cached_price kayıtları
    Dış bağlam: Google aramasından indirim/fırsat odaklı sonuçlar
    """
    try:
        firebase_uid = current_user.get("uid")
        logger.info(f"Comprehensive analysis request from user {firebase_uid}")

        # User ID al
        user = await user_service.get_user_by_firebase_uid(firebase_uid)
        if not user or not user.get("id"):
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

        # 1) İç bağlamı topla (aktif abonelikler + cached prices)
        internal_context = await analysis_context_service.get_comprehensive_analysis_context(user_id)

        # 2) İndirim odaklı Google aramasını hazırla (abonelik isimlerinden)
        #    Mevcut abonelik listesi için isimleri al
        subs_result = await subscription_service.get_subscriptions(
            user_id=user_id,
            is_active=True,
            page=1,
            limit=100
        )
        subs = subs_result.get("subscriptions", []) if isinstance(subs_result, dict) else []
        user_bill_names = [s.get("name") for s in subs if s.get("name")]

        search_query = google_search_service.generate_discount_opportunities_query(user_bill_names)

        # 3) Google’da ara – indirim ve tasarruf fırsatları
        google_results = await google_search_service.search_google(
            search_query,
            num_results=5,
            gl="tr",
            lr="lang_tr"
        )

        external_context_parts: List[str] = []
        if google_results:
            for i, r in enumerate(google_results, 1):
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                link = r.get("link", "")
                external_context_parts.append(
                    f"Kaynak {i}: {title} - {snippet} ({link})"
                )
        external_context = "\n".join(external_context_parts) if external_context_parts else "İndirim bilgisi bulunamadı."

        # 4) Gemini için özel prompt’u hazırla (tamamen yeni format)
        full_prompt = f"""
BAĞLAM (İÇ):
{internal_context}

BAĞLAM (DIŞ - İNDİRİM VE FIRSATLAR):
{external_context}

GÖREV: Sen bir finansal analist yapay zekasın. Sana kullanıcının mevcut fatura listesi ve güncel piyasa fiyatları (BAĞLAM) verildi. Görevin, kullanıcının kâr etmesi ve tasarruf etmesi için yüksek etkili 10 öneri sunmaktır.

ODAĞIN:
1) Kullanıcının kendi fiyatı ile cached_price arasındaki farkı gösteren uyarılar.
2) İndirim kodları / kampanya fırsatları (Google sonuçlarından).
3) Alternatif plan veya hizmet önerileri (daha ucuz seçenekler).

KURALLAR:
- Türkçe yanıt ver.
- Yapılandırılmış, anlaşılır rapor üret; başlık ve numaralı 10 madde kullan.
- Her maddede kısa gerekçe ve mümkünse tahmini aylık/yıllık tasarruf aralığı belirt.
- BAĞLAM’da bulunmayan bilgiyi uydurma; yetersizse “bağlamda yeterli kanıt yok” de.
- Sonunda “Hızlı Özet” bölümünde en kritik 3 aksiyonu listele.

YANIT:
"""

        # 5) Gemini’ye gönder (özel raw prompt)
        report_text = await gemini_service.ask_gemini_raw(full_prompt)
        if not report_text:
            report_text = "Bağlamdan faydalanarak 10 maddelik bir tasarruf raporu üretilemedi. Lütfen daha sonra tekrar deneyin."

        logger.info(f"Comprehensive analysis completed for user {firebase_uid}")

        return {
            "success": True,
            "message": "Analiz tamamlandı",
            "data": {
                "report_text": report_text,
                "search_query": search_query,
                "sources_found": len(google_results or []),
                "format": "text_report"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}")
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