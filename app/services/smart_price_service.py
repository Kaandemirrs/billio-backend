import re
from decimal import Decimal
from typing import Dict, Any, List, Optional
import logging

from tavily import TavilyClient

from app.config import settings
from app.services.gemini_service import gemini_service


logger = logging.getLogger(__name__)


class SmartPriceService:
    def __init__(self) -> None:
        if not settings.TAVILY_API_KEY:
            logger.error("TAVILY_API_KEY not configured in settings")
        self.tavily = TavilyClient(api_key=settings.TAVILY_API_KEY or "")

    async def find_price(self, service_name: str, plan_name: str) -> Dict[str, Any]:
        if not service_name or not plan_name:
            logger.warning("SmartPriceService.find_price called with empty service_name or plan_name")
            print("[SmartPriceService] Geçersiz giriş: service_name veya plan_name boş")
            return {
                "price": None,
                "currency": "TRY",
                "source": None,
                "confidence": "low",
            }

        query = f"{service_name} {plan_name} üyelik ücreti fiyatı 2025 Türkiye güncel"

        print(f"[SmartPriceService] Tavily araması başlatılıyor. Sorgu: {query}")
        logger.info(f"SmartPriceService Tavily search query: {query}")

        tavily_kwargs: Dict[str, Any] = {
            "query": query,
            "search_depth": "advanced",
            "max_results": 5,
        }

        try:
            response = self.tavily.search(**tavily_kwargs)
        except Exception as e:
            print(f"[SmartPriceService] Tavily araması hata verdi: {str(e)}")
            logger.error(f"SmartPriceService Tavily error: {str(e)}")
            return {
                "price": None,
                "currency": "TRY",
                "source": None,
                "confidence": "low",
            }

        if not response or not isinstance(response, dict):
            print("[SmartPriceService] Tavily yanıtı geçersiz")
            logger.warning("SmartPriceService Tavily response invalid")
            return {
                "price": None,
                "currency": "TRY",
                "source": None,
                "confidence": "low",
            }

        results = response.get("results") or []
        if not results:
            print("[SmartPriceService] Tavily sonuç döndürmedi")
            logger.info("SmartPriceService Tavily returned no results")
            return {
                "price": None,
                "currency": "TRY",
                "source": None,
                "confidence": "low",
            }

        contents: List[str] = []
        primary_source: Optional[str] = None
        for idx, r in enumerate(results, start=1):
            r = r or {}
            c = r.get("content") or ""
            if not c:
                continue
            contents.append(c)
            if not primary_source:
                primary_source = r.get("url")
            print(f"[SmartPriceService] Tavily sonucu {idx} içerik uzunluğu: {len(c)}")

        if not contents:
            print("[SmartPriceService] Tavily sonuçlarında içerik bulunamadı")
            logger.info("SmartPriceService Tavily results had no content")
            return {
                "price": None,
                "currency": "TRY",
                "source": primary_source,
                "confidence": "low",
            }

        combined_content = "\n\n".join(contents)

        print(f"[SmartPriceService] Tavily birleşik içerik uzunluğu: {len(combined_content)}")
        print(f"[SmartPriceService] Tavily Raw Content: {combined_content[:500]}...")
        logger.info(f"SmartPriceService Tavily combined content length: {len(combined_content)}")

        system_prompt = (
            "Sen bir fiyat araştırma asistanısın. Aşağıda farklı kaynaklardan "
            "(haber siteleri, bloglar, resmi siteler) arama sonuçları var. "
            "Görevin:\n"
            "1. Bu metinler arasındaki EN GÜNCEL (2025) ve ortak fiyatı tespit et.\n"
            "2. Eski (2024 veya öncesi) fiyatları yoksay.\n"
            "3. Sadece Türkiye (TL) fiyatını bul.\n"
            "4. Yanıt olarak sadece sayıyı ver (Örn: 229.99). Para birimi veya ek metin yazma."
        )

        full_prompt = f"{system_prompt}\n\nMETİN:\n{combined_content}"

        print(f"[SmartPriceService] Gemini isteği hazırlanıyor")
        logger.info("SmartPriceService sending prompt to Gemini for price extraction")

        raw_response = await gemini_service.ask_gemini_raw(full_prompt)

        print(f"[SmartPriceService] Gemini ham yanıtı: {raw_response}")
        logger.info(f"SmartPriceService Gemini raw response: {raw_response}")

        if not raw_response:
            print("[SmartPriceService] Gemini'den yanıt alınamadı")
            return {
                "price": None,
                "currency": "TRY",
                "source": primary_source,
                "confidence": "low",
            }

        raw_text = str(raw_response).strip()
        if raw_text == "0":
            price_decimal = Decimal(0)
        else:
            price_decimal = _extract_decimal(raw_text)

        print(f"[SmartPriceService] Parse edilen fiyat: {price_decimal}")
        logger.info(f"SmartPriceService parsed price: {price_decimal}")

        if price_decimal is None or price_decimal == 0:
            confidence = "low"
            price_value = None
        else:
            confidence = "high"
            price_value = float(price_decimal)

        return {
            "price": price_value,
            "currency": "TRY",
            "source": primary_source,
            "confidence": confidence,
        }


def _extract_decimal(text: str) -> Optional[Decimal]:
    m = re.search(r"(\d{1,5}[\.,]\d{1,2})", text)
    if not m:
        m2 = re.search(r"(\d{3,6})", text)
        if not m2:
            return None
        try:
            return Decimal(m2.group(1))
        except Exception:
            return None
    val = m.group(1).replace(",", ".")
    try:
        return Decimal(val)
    except Exception:
        return None


smart_price_service = SmartPriceService()
