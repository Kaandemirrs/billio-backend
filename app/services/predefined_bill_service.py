from app.core.supabase import get_supabase_admin_client
from typing import List, Dict, Optional
import time

class PredefinedBillService:
    """Predefined bills service"""

    def __init__(self):
        self.supabase = get_supabase_admin_client()
        self._popular_cache: Optional[Dict] = None
        self._popular_cache_ttl_sec = 60  # simple cache TTL

    async def get_all(self) -> List[Dict]:
        """Tüm predefined bills listesi"""
        try:
            result = self.supabase.table("predefined_bills").select("*").order("sort_order").execute()
            return result.data or []
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")

    async def get_popular(self) -> List[Dict]:
        """Popüler predefined bills (cache'lenebilir)"""
        try:
            now = time.time()
            if self._popular_cache and (now - self._popular_cache.get("ts", 0) < self._popular_cache_ttl_sec):
                return self._popular_cache.get("data", [])

            result = self.supabase.table("predefined_bills").select("*").eq("is_popular", True).order("sort_order").execute()
            data = result.data or []
            self._popular_cache = {"ts": now, "data": data}
            return data
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")

    async def search(self, q: str) -> List[Dict]:
        """Arama: service_name ve display_name ilike"""
        try:
            # limit 10
            query = self.supabase.table("predefined_bills").select("*").or_(
                f"service_name.ilike.%{q}%,display_name.ilike.%{q}%"
            ).limit(10)
            result = query.execute()
            return result.data or []
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")

# Singleton instance
predefined_bill_service = PredefinedBillService()