import re
from decimal import Decimal
from typing import Dict, Any, List, Optional
import logging

from tavily import TavilyClient

from app.config import settings
from app.services.gemini_service import gemini_service


logger = logging.getLogger(__name__)


OFFICIAL_DOMAINS: Dict[str, List[str]] = {
    "netflix": ["netflix.com"],
    "spotify": ["spotify.com"],
    "exxen": ["exxen.com"],
    "disneyplus": ["disneyplus.com", "disneyplus.com.tr"],
    "amazonprimevideo": ["primevideo.com", "amazon.com"],
}


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

        service_key = _normalize_service_key(service_name)
        query = f"{service_name} {plan_name} fiyatı Türkiye 2025"

        print(f"[SmartPriceService] Tavily araması başlatılıyor. Sorgu: {query}")
        logger.info(f"SmartPriceService Tavily search query: {query}")

        tavily_kwargs: Dict[str, Any] = {
            "query": query,
            "search_depth": "advanced",
            "max_results": 1,
        }

        include_domains = OFFICIAL_DOMAINS.get(service_key)
        if include_domains:
            tavily_kwargs["include_domains"] = include_domains

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

        first_result = results[0] or {}
        content = first_result.get("content") or ""
        primary_source: Optional[str] = first_result.get("url")

        print(f"[SmartPriceService] Tavily'den gelen içerik uzunluğu: {len(content)}")
        logger.info(f"SmartPriceService Tavily content length: {len(content)}")

        system_prompt = (
            f"Sen bir fiyat analiz uzmanısın. Görevin: Aşağıdaki metin içinden "
            f"SADECE '{service_name}' servisine ait '{plan_name}' (veya en yakın eşleşen plan) "
            f"için geçerli AYLIK fiyatı bul.\n"
            f"Kurallar:\n"
            f"1. Sadece Türkiye (TL) fiyatını al.\n"
            f"2. Yanıt olarak SADECE sayıyı ver (Örn: 229.99). Para birimi veya metin yazma.\n"
            f"3. Eğer metinde '{plan_name}' için net bir fiyat yoksa veya emin değilsen '0' döndür. Asla tahmin yapma."
        )

        full_prompt = f"{system_prompt}\n\nMETİN:\n{content}"

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


def _normalize_service_key(name: str) -> str:
    return re.sub(r"\s+|\+", "", name or "").lower()


def _extract_decimal(text: str) -> Optional[Decimal]:
    m = re.search(r"(\d{1,5}[\.,]\d{1,2})", text)
    if not m:
        m2 = re.search(r"(\d{2,6})", text)
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
