import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1 import auth, user, subscriptions, analytics, ai, notifications, premium, categories, predefined_bills, services_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.ai_cron_service import update_all_plan_prices
from app.core.firebase import initialize_firebase
from app.core.rate_limiter import rate_limiter
from app.config import settings

# Debug mode kontrolü
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

# FastAPI instance
app = FastAPI(
    title="🎯 " + settings.APP_NAME,
    description="""
# 🚀 Billio API - Subscription Tracking Platform

Billio, abonelik yönetimi ve AI destekli tasarruf önerileri sunan bir platformdur.

## 📊 API İstatistikleri

| Modül | Endpoint Sayısı | Açıklama |
|-------|----------------|----------|
| **👤 Users** | 8 endpoint | Kullanıcı yönetimi, profil, telefon doğrulama, ayarlar |
| **💳 Subscriptions** | 6 endpoint | Abonelik ekleme, düzenleme, silme, listeleme |
| **📈 Analytics** | 2 endpoint | Harcama özeti, trendler, kategorik analiz |
| **🤖 AI Analysis** | 8 endpoint | AI destekli tasarruf önerileri, bulk analiz |
| **🔔 Notifications** | 8 endpoint | Bildirim yönetimi, hatırlatıcılar |
| **💎 Premium** | 10 endpoint | Premium satın alma, iptal, fatura yönetimi |
| **📂 Categories** | 2 endpoint | Kategori listesi, istatistikler |

### 🎊 **Toplam: 44 Endpoint**

---

## 🔑 Özellikler

### 🔐 Authentication
- **Firebase JWT** token bazlı kimlik doğrulama
- Her endpoint `Authorization: Bearer <token>` header'ı gerektirir
- `sync-user` endpoint'i ile otomatik kullanıcı kaydı

### 👤 Users Module
- ✅ Kullanıcı profil yönetimi
- ✅ Telefon numarası doğrulama (SMS)
- ✅ Ayarlar (dil, para birimi, tema)
- ✅ Hesap silme (KVKK uyumlu)

### 💳 Subscriptions Module
- ✅ Abonelik CRUD operasyonları
- ✅ Kategori bazında filtreleme
- ✅ Aktif/Pasif durumu yönetimi
- ✅ Aylık/Yıllık harcama özeti
- ✅ Pagination desteği

### 📈 Analytics Module
- ✅ Genel harcama özeti (aylık, yıllık)
- ✅ Kategori bazında breakdown
- ✅ 12 aylık trend analizi
- ✅ En yüksek harcamalar (top subscriptions)

### 🤖 AI Analysis Module (Premium)
- ✅ Tek abonelik AI analizi
- ✅ Toplu analiz (bulk-analyze)
- ✅ Tasarruf önerileri
- ✅ Öneri uygulama
- ✅ Geri bildirim sistemi
- ✅ Analiz geçmişi

### 🔔 Notifications Module
- ✅ Ödeme hatırlatıcıları
- ✅ Fiyat değişikliği bildirimleri
- ✅ Tasarruf fırsatları
- ✅ Okundu/Okunmadı yönetimi
- ✅ Toplu işlemler

### 💎 Premium Module
- ✅ Premium plan listesi (Aylık, Yıllık, Lifetime)
- ✅ Premium satın alma (Mock & Live mode)
- ✅ Ödeme doğrulama
- ✅ Fatura yönetimi
- ✅ İptal ve yeniden aktifleştirme
- ✅ Webhook entegrasyonu (Stripe, Iyzico)

### 📂 Categories Module
- ✅ Kategori listesi (icon, renk, açıklama)
- ✅ Kategori bazında istatistikler
- ✅ Çoklu dil desteği (TR/EN)

---

## 🛠️ Teknolojiler

- **Framework:** FastAPI
- **Authentication:** Firebase Admin SDK
- **Database:** Supabase (PostgreSQL)
- **Payment:** Mock Mode (Stripe/Iyzico hazır)
- **AI:** Mock AI (OpenAI/Claude entegrasyonu hazır)

---

## 📖 Kullanım

### 1. Token Al
```bash
POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=YOUR_API_KEY
Body: {"email": "user@example.com", "password": "password", "returnSecureToken": true}
```

### 2. User Sync
```bash
POST /api/v1/auth/sync-user
Authorization: Bearer <firebase_token>
Body: {"full_name": "John Doe"}
```

### 3. Abonelik Ekle
```bash
POST /api/v1/subscriptions
Authorization: Bearer <firebase_token>
Body: {
  "name": "Netflix",
  "category": "entertainment",
  "amount": 149.99,
  "currency": "TRY",
  "billing_cycle": "monthly",
  "billing_day": 15,
  "start_date": "2025-10-15"
}
```

### 4. AI Analizi
```bash
POST /api/v1/ai/analyze/{subscription_id}
Authorization: Bearer <firebase_token>
```

---

## 🚀 Test Modu

### Mock Payment
Premium satın almak için:
```json
{
  "plan_type": "yearly",
  "payment_method": "mock",
  "payment_token": "mock_token_test123"
}
```

### Mock AI
AI analiz endpoint'leri otomatik mock veri döner. Gerçek AI entegrasyonu için `OPENAI_API_KEY` ekleyin.

---

## 📞 İletişim

- **Version:** 1.0.0
- **Environment:** Development
- **Base URL:** http://localhost:8001

---

## ⚡ Hızlı Linkler

- 📄 [API Documentation](/docs)
- 🔄 [ReDoc](/redoc)
- 🌐 [GitHub Repository](https://github.com/yourusername/billio-backend)

    """,
    version=settings.APP_VERSION,
    docs_url="/docs" if DEBUG_MODE else None,
    redoc_url="/redoc" if DEBUG_MODE else None,
    openapi_url="/openapi.json" if DEBUG_MODE else None,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "🔐 Firebase token ile kullanıcı kimlik doğrulama ve senkronizasyon"
        },
        {
            "name": "User",
            "description": "👤 Kullanıcı profili, telefon doğrulama, ayarlar, hesap yönetimi (8 endpoint)"
        },
        {
            "name": "Subscriptions",
            "description": "💳 Abonelik CRUD, listeleme, filtreleme, özet bilgiler (6 endpoint)"
        },
        {
            "name": "Analytics",
            "description": "📈 Harcama özeti, trendler, kategori analizi (2 endpoint)"
        },
        {
            "name": "AI Analysis",
            "description": "🤖 AI destekli tasarruf önerileri, bulk analiz, geri bildirim (8 endpoint)"
        },
        {
            "name": "Notifications",
            "description": "🔔 Bildirim yönetimi, hatırlatıcılar, okundu/okunmadı (8 endpoint)"
        },
        {
            "name": "Premium",
            "description": "💎 Premium satın alma, iptal, fatura yönetimi, webhook (10 endpoint)"
        },
        {
            "name": "Categories",
            "description": "📂 Kategori listesi, istatistikler, çoklu dil desteği (2 endpoint)"
        },
        {
            "name": "Predefined Bills",
            "description": "📚 Önceden tanımlı servisler: liste, popüler, arama"
        }
    ]
)

# APScheduler instance
scheduler = AsyncIOScheduler()

# CORS Middleware
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8001")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)

# Rate limiter middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Public endpoint'ler için rate limit uygula
    if not request.url.path.startswith("/docs") and not request.url.path.startswith("/openapi"):
        await rate_limiter.check_rate_limit(request)
    
    response = await call_next(request)
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global hata yakalayıcı"""
    
    # Debug mode'da detaylı hata
    if DEBUG_MODE:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(exc),
                    "detail": str(exc.__class__.__name__)
                }
            }
        )
    
    # Production'da genel hata
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Bir hata oluştu. Lütfen daha sonra tekrar deneyin."
            }
        }
    )

# Root endpoint
@app.get("/")
async def root():
    return {
        "success": True,
        "message": "Billio API is running! 🚀",
        "version": settings.APP_VERSION
    }

# Health check
@app.get("/health")
async def health_check():
    return {
        "success": True,
        "status": "healthy",
        "message": "API is working fine"
    }

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Authentication"])
app.include_router(user.router, prefix=settings.API_V1_PREFIX, tags=["User"])
app.include_router(subscriptions.router, prefix=settings.API_V1_PREFIX, tags=["Subscriptions"])
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX, tags=["Analytics"])
app.include_router(ai.router, prefix=settings.API_V1_PREFIX, tags=["AI Analysis"])
app.include_router(notifications.router, prefix=settings.API_V1_PREFIX, tags=["Notifications"])
app.include_router(premium.router, prefix=settings.API_V1_PREFIX, tags=["Premium"])
app.include_router(categories.router, prefix=settings.API_V1_PREFIX, tags=["Categories"])
app.include_router(predefined_bills.router, prefix=settings.API_V1_PREFIX, tags=["Predefined Bills"])
app.include_router(services_router.router, prefix=f"{settings.API_V1_PREFIX}/services", tags=["Services & Plans"]) 

# Startup event
@app.on_event("startup")
async def startup_event():
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} başlatıldı!")
    print(f"📄 Swagger Docs: http://localhost:8001/docs")
    
    # Firebase initialize
    try:
        initialize_firebase()
    except Exception as e:
        print(f"⚠️ Firebase başlatılamadı: {e}")

    # Cron Job: AI fiyat güncelleme
    try:
        if DEBUG_MODE:
            # Test: her 4 saatte bir çalıştır
            scheduler.add_job(update_all_plan_prices, "interval", hours=4)
        else:
            # Prod: Pazar günleri saat 03:00'te çalıştır
            scheduler.add_job(update_all_plan_prices, "cron", day_of_week="sun", hour=3)
        scheduler.start()
        print("🕰️ APScheduler başlatıldı ve AI fiyat güncelleme job'ı eklendi.")

        # Test için: başlangıçta bir kez hemen çalıştır
        if DEBUG_MODE:
            # İlk run (await)
            try:
                await update_all_plan_prices()
                print("✅ İlk AI fiyat güncelleme çalıştırıldı (DEBUG mode)")
            except Exception as e:
                print(f"⚠️ İlk AI fiyat güncelleme başarısız: {e}")
    except Exception as e:
        print(f"⚠️ APScheduler başlatılamadı: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print("👋 Billio API kapatılıyor...")
    try:
        scheduler.shutdown(wait=False)
        print("🛑 APScheduler durduruldu.")
    except Exception as e:
        print(f"⚠️ APScheduler durdurulamadı: {e}")
