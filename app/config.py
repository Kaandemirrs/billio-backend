from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Billio API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Firebase (Opsiyonel yapıldı - JSON veya dosya yolundan okunabilir)
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = None
    FIREBASE_SERVICE_ACCOUNT_JSON: Optional[str] = None  # Yeni eklendi
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str
    
    # AI Services
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_ENGINE_ID: Optional[str] = None
    VERTEX_AI_SERVICE_ACCOUNT_JSON: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    # API
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Settings instance
settings = Settings()
import logging
logger = logging.getLogger(__name__)

# --- YENİ DEBUG KODU ---
logger.warning("--- ÇEVRE DEĞİŞKENLERİ KONTROL EDİLİYOR ---")

if settings.GOOGLE_SEARCH_API_KEY:
    logger.warning("Config Check: GOOGLE_SEARCH_API_KEY başarıyla yüklendi.")
else:
    logger.error("Config Check: HATA! GOOGLE_SEARCH_API_KEY bulunamadı!")

if settings.GOOGLE_SEARCH_ENGINE_ID:
    logger.warning("Config Check: GOOGLE_SEARCH_ENGINE_ID başarıyla yüklendi.")
else:
    logger.error("Config Check: HATA! GOOGLE_SEARCH_ENGINE_ID bulunamadı!")

if settings.VERTEX_AI_SERVICE_ACCOUNT_JSON:
    logger.warning("Config Check: VERTEX_AI_SERVICE_ACCOUNT_JSON başarıyla yüklendi.")
else:
    logger.error("Config Check: HATA! VERTEX_AI_SERVICE_ACCOUNT_JSON bulunamadı!")

logger.warning("--- KONTROL TAMAMLANDI ---")
# --- BİTTİ ---
