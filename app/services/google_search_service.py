import httpx
from typing import List, Dict, Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class GoogleSearchService:
    def __init__(self):
        self.api_key = settings.GOOGLE_SEARCH_API_KEY
        self.search_engine_id = settings.GOOGLE_SEARCH_ENGINE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        if not self.api_key:
            logger.warning("Google Search API key not configured in settings (GOOGLE_SEARCH_API_KEY)")
        if not self.search_engine_id:
            logger.warning("Google Search Engine ID not configured in settings (GOOGLE_SEARCH_ENGINE_ID)")

    def generate_discount_opportunities_query(self, user_bills_names: List[str]) -> str:
        """
        Kullanıcının abonelik isimlerinden indirim ve tasarruf odaklı bir arama sorgusu oluşturur.

        Örnek Template:
        "{user_bills_names} abonelik indirimleri, alternatif fiyatlar ve tasarruf fırsatları"
        """
        cleaned = [name.strip() for name in (user_bills_names or []) if isinstance(name, str) and name.strip()]
        joined = ", ".join(cleaned) if cleaned else "abonelik"
        return f"{joined} abonelik indirimleri, alternatif fiyatlar ve tasarruf fırsatları"
    
    async def search_google(self, query: str, num_results: int = 5, gl: Optional[str] = None, lr: Optional[str] = None, hl: Optional[str] = None) -> List[Dict]:
        """
        Google Custom Search API kullanarak arama yapar
        
        Args:
            query (str): Arama sorgusu
            num_results (int): Döndürülecek sonuç sayısı (maksimum 10)
            
        Returns:
            List[Dict]: Arama sonuçları listesi
        """
        if not self.api_key or not self.search_engine_id:
            logger.error("Google Search API key not configured")
            return []
        
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return []
        
        try:
            params = {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": query.strip(),
                "num": min(num_results, 10)
            }
            if gl:
                params["gl"] = gl
            if lr:
                params["lr"] = lr
            if hl:
                params["hl"] = hl
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Sonuçları işle
                results = []
                if "items" in data:
                    for item in data["items"]:
                        result = {
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "snippet": item.get("snippet", ""),
                            "displayLink": item.get("displayLink", "")
                        }
                        results.append(result)
                
                logger.info(f"Google search completed for query: '{query}', found {len(results)} results")
                return results
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Google Search API HTTP error: {e.response.status_code} - {e.response.text}")
            return []
        except httpx.TimeoutException:
            logger.error("Google Search API request timeout")
            return []
        except Exception as e:
            logger.error(f"Google Search API error: {str(e)}")
            return []

# Singleton instance
google_search_service = GoogleSearchService()
