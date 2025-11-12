import re
from typing import Optional, List, Dict
from decimal import Decimal
from datetime import datetime, timezone

from app.core.supabase import get_supabase_admin_client
from app.services.google_search_service import google_search_service
from app.services.gemini_service import gemini_service


async def update_all_plan_prices() -> Dict[str, int]:
    """
    Tüm service_plans kayıtları için AI/RAG ile fiyat bul ve veritabanını güncelle.

    Returns:
        Özet: {"processed": N, "updated": M, "skipped": K}
    """
    supabase = get_supabase_admin_client()

    # Tüm planları çek
    plans_res = supabase.table("service_plans").select("*").execute()
    plans: List[Dict] = plans_res.data or []

    if not plans:
        return {"processed": 0, "updated": 0, "skipped": 0}

    # Servisleri önceden map'le (id -> service row)
    services_res = supabase.table("services").select("id,name,display_name").execute()
    services: Dict[str, Dict] = {row["id"]: row for row in (services_res.data or [])}

    processed = 0
    updated = 0
    skipped = 0

    for plan in plans:
        processed += 1
        service_row = services.get(plan.get("service_id"))
        if not service_row:
            skipped += 1
            continue

        service_name = service_row.get("name") or service_row.get("display_name")
        plan_name = plan.get("plan_name")

        price = await _find_price_with_smart_rag(service_name, plan_name)
        if price is None:
            skipped += 1
            continue

        # Supabase update
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            supabase.table("service_plans").update({
                "cached_price": float(price),  # Supabase numeric/decimal için float kabul ediyor
                "currency": "TRY",
                "last_updated_ai": now_iso,
            }).eq("id", plan.get("id")).execute()
            updated += 1
        except Exception:
            skipped += 1

    return {"processed": processed, "updated": updated, "skipped": skipped}


async def _find_price_with_smart_rag(service_name: str, plan_name: str) -> Optional[Decimal]:
    """
    Google araması (TR locale) + resmi domain filtreleme + Gemini ile sadece fiyat çıkarımı.
    """
    if not service_name or not plan_name:
        return None

    # Sorgu: Türkiye odaklı
    query = f"{service_name} {plan_name} Türkiye fiyatı"

    # Zorunlu TR ayarları
    results = await google_search_service.search_google(query=query, num_results=6, gl="tr", lr="lang_tr")
    if not results:
        return None

    # Halüsinasyon önleyici: resmi domain filtreleme
    service_key = _normalize_service_key(service_name)
    official_results = [r for r in results if _is_official_domain(r.get("displayLink", ""), service_key)]

    if not official_results:
        return None

    # Bağlamı oluştur
    context_parts = []
    for r in official_results:
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        link = r.get("link", "")
        context_parts.append(f"Title: {title}\nSnippet: {snippet}\nLink: {link}")
    context = "\n\n".join(context_parts)

    # Gemini: sadece sayısal fiyat çıkar
    prompt = (
        "Aşağıdaki bağlamdan yalnızca parasal fiyatı çıkar. "
        "Sadece sayı olarak cevap ver (ör: 229.99). Para birimi yazma, metin yazma. "
        "Bağlamda birden fazla fiyat varsa en güncel ve bireysel plan fiyatını tercih et."
    )

    text = await gemini_service.ask_gemini(context=context, prompt=prompt)
    if not text:
        return None

    # İlk sayı/decimal'i yakala
    price = _extract_decimal(text)
    return price


def _normalize_service_key(name: str) -> str:
    return re.sub(r"\s+", "", name or "").lower()


def _is_official_domain(display_link: str, service_key: str) -> bool:
    dl = (display_link or "").lower()
    # Basit eşleşme: service adını içeren domain veya .com/.com.tr varyasyonları
    return service_key in dl or dl.startswith(f"{service_key}.") or dl.endswith(f".{service_key}.com")


def _extract_decimal(text: str) -> Optional[Decimal]:
    # 199,99 veya 199.99 gibi formatları yakala; virgülü noktaya çevir
    m = re.search(r"(\d{1,5}[\.,]\d{1,2})", text)
    if not m:
        # Tam sayı fiyat olabilir (ör: 229)
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