import re
from decimal import Decimal
from typing import Dict, Any, List, Optional
import logging

from app.services.google_search_service import google_search_service
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
        self.official_domains = OFFICIAL_DOMAINS

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

        query = f"{service_name} Türkiye {plan_name} aylık ücret fiyatı 2025"
        print(f"[SmartPriceService] Google araması başlatılıyor. Sorgu: {query}")
        logger.info(f"SmartPriceService Google search query: {query}")

        results = await google_search_service.search_google(
            query=query,
            num_results=6,
            gl="tr",
            lr="lang_tr",
            hl="tr",
        )

        print(f"[SmartPriceService] Google araması tamamlandı. Toplam sonuç: {len(results)}")
        logger.info(f"SmartPriceService Google search returned {len(results)} results")

        if not results:
            print("[SmartPriceService] Google aramasından sonuç dönmedi")
            return {
                "price": None,
                "currency": "TRY",
                "source": None,
                "confidence": "low",
            }

        service_key = _normalize_service_key(service_name)
        official_results = self._filter_official_results(results, service_key)

        print(f"[SmartPriceService] Resmi domain filtrelemesi sonrası sonuç sayısı: {len(official_results)}")
        logger.info(f"SmartPriceService official results count: {len(official_results)}")

        if not official_results:
            print("[SmartPriceService] Resmi domain ile eşleşen sonuç bulunamadı")
            return {
                "price": None,
                "currency": "TRY",
                "source": None,
                "confidence": "low",
            }

        snippets = []
        primary_source: Optional[str] = None
        for idx, r in enumerate(official_results, start=1):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            link = r.get("link", "")
            if not primary_source and link:
                primary_source = link
            snippets.append(snippet)
            print(f"[SmartPriceService] Resmi kaynak {idx}: {title} | {link}")

        context_text = "\n".join(snippets)
        print(f"[SmartPriceService] Gemini'ye gidecek snippet metni: {context_text}")

        system_prompt = (
            f"Sen bir fiyat analiz uzmanısın. Görevin: Aşağıdaki metin içinden "
            f"SADECE '{service_name}' servisine ait '{plan_name}' (veya en yakın eşleşen plan) "
            f"için geçerli AYLIK fiyatı bul.\n"
            f"Kurallar:\n"
            f"1. Sadece Türkiye (TL) fiyatını al.\n"
            f"2. Yanıt olarak SADECE sayıyı ver (Örn: 229.99). Para birimi veya metin yazma.\n"
            f"3. Eğer metinde '{plan_name}' için net bir fiyat yoksa veya emin değilsen '0' döndür. Asla tahmin yapma."
        )

        full_prompt = f"{system_prompt}\n\nMETİN:\n{context_text}"

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

    def _filter_official_results(
        self,
        results: List[Dict[str, Any]],
        service_key: str,
    ) -> List[Dict[str, Any]]:
        official_domains = self.official_domains.get(service_key)

        filtered: List[Dict[str, Any]] = []
        for r in results:
            link = (r.get("link") or "").lower()
            display_link = (r.get("displayLink") or "").lower()

            if official_domains:
                if any(d in link or d in display_link for d in official_domains):
                    filtered.append(r)
            else:
                if service_key and (
                    service_key in link
                    or service_key in display_link
                    or link.startswith(f"{service_key}.")
                    or display_link.startswith(f"{service_key}.")
                ):
                    filtered.append(r)

        return filtered


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
