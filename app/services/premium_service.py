from app.core.supabase import get_supabase_admin_client
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import os
import hmac
import hashlib
import json
try:
    import stripe
except Exception:
    stripe = None

class PremiumService:
    """Premium/Payment service"""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
        self.payment_mode = os.getenv("PAYMENT_MODE", "mock")  # mock or live
    
    def get_plans(self) -> List[Dict]:
        """Premium planları getir (hardcoded)"""
        return [
            {
                "id": "monthly",
                "name": "Aylık Premium",
                "description": "Her ay yenilenen premium abonelik",
                "price": 49.99,
                "currency": "TRY",
                "billing_cycle": "monthly",
                "features": [
                    "Sınırsız AI analiz",
                    "Toplu analiz yapabilme",
                    "Gelişmiş raporlar",
                    "Fiyat takibi ve uyarıları",
                    "Öncelikli destek",
                    "Reklamsız deneyim"
                ],
                "popular": False
            },
            {
                "id": "yearly",
                "name": "Yıllık Premium",
                "description": "Yıllık ödeme ile %40 tasarruf",
                "price": 399.99,
                "original_price": 599.88,
                "currency": "TRY",
                "billing_cycle": "yearly",
                "savings": "₺199,89 tasarruf!",
                "features": [
                    "Tüm aylık özellikler",
                    "2 ay bedava",
                    "Özel danışmanlık hizmeti",
                    "Erken erişim özellikleri"
                ],
                "popular": True
            },
            {
                "id": "lifetime",
                "name": "Ömür Boyu Premium",
                "description": "Tek seferlik ödeme, ömür boyu kullanım",
                "price": 1499.99,
                "currency": "TRY",
                "billing_cycle": "lifetime",
                "savings": "Sınırsız kullanım!",
                "features": [
                    "Tüm premium özellikler",
                    "Ömür boyu güncellemeler",
                    "VIP destek",
                    "Gelecekteki tüm özellikler"
                ],
                "popular": False
            }
        ]
    
    def get_features(self) -> List[Dict]:
        """Premium özellikleri getir"""
        return [
            {
                "id": "unlimited_ai",
                "name": "Sınırsız AI Analiz",
                "description": "Tüm aboneliklerinizi AI ile analiz edin",
                "icon": "🤖"
            },
            {
                "id": "bulk_analysis",
                "name": "Toplu Analiz",
                "description": "Tüm aboneliklerinizi tek seferde analiz edin",
                "icon": "📊"
            },
            {
                "id": "advanced_reports",
                "name": "Gelişmiş Raporlar",
                "description": "Detaylı harcama raporları ve trendler",
                "icon": "📈"
            },
            {
                "id": "price_tracking",
                "name": "Fiyat Takibi",
                "description": "Abonelik fiyat değişikliklerini otomatik takip edin",
                "icon": "💰"
            },
            {
                "id": "priority_support",
                "name": "Öncelikli Destek",
                "description": "7/24 öncelikli müşteri desteği",
                "icon": "🎯"
            }
        ]
    
    async def get_status(self, user_id: str) -> Dict:
        """Kullanıcının premium durumunu getir"""
        try:
            # User bilgilerini al
            user_result = self.supabase.table("users").select(
                "subscription_type, premium_expires_at"
            ).eq("id", user_id).execute()
            
            if not user_result.data or len(user_result.data) == 0:
                raise Exception("Kullanıcı bulunamadı")
            
            user = user_result.data[0]
            subscription_type = user.get("subscription_type", "free")
            premium_expires_at = user.get("premium_expires_at")
            
            if subscription_type == "premium" and premium_expires_at:
                # Premium user
                expires_at = datetime.fromisoformat(premium_expires_at.replace('Z', '+00:00'))
                now = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
                days_remaining = (expires_at - now).days
                
                # Son satın almayı al
                purchase_result = self.supabase.table("premium_purchases").select("*").eq(
                    "user_id", user_id
                ).eq("status", "active").order("created_at", desc=True).limit(1).execute()
                
                plan_type = "unknown"
                starts_at = None
                if purchase_result.data and len(purchase_result.data) > 0:
                    purchase = purchase_result.data[0]
                    plan_type = purchase.get("plan_type", "unknown")
                    starts_at = purchase.get("starts_at")
                
                return {
                    "is_premium": True,
                    "plan_type": plan_type,
                    "starts_at": starts_at,
                    "expires_at": premium_expires_at,
                    "days_remaining": days_remaining if days_remaining > 0 else 0,
                    "auto_renewal": True,
                    "features": [
                        "unlimited_ai_analysis",
                        "bulk_analysis",
                        "advanced_reports",
                        "price_tracking",
                        "priority_support"
                    ],
                    "usage_stats": {
                        "ai_analyses_used": 0,  # TODO: Gerçek veri
                        "ai_analyses_limit": None,
                        "bulk_analyses_used": 0
                    }
                }
            else:
                # Free user
                return {
                    "is_premium": False,
                    "plan_type": "free",
                    "features": [
                        "basic_tracking",
                        "manual_entry"
                    ],
                    "limitations": {
                        "ai_analyses_limit": 0,
                        "max_subscriptions": 10
                    },
                    "upgrade_benefits": [
                        "Sınırsız AI analiz",
                        "Gelişmiş raporlar",
                        "Toplu analiz"
                    ]
                }
            
        except Exception as e:
            raise Exception(f"Get status error: {str(e)}")
    
    async def purchase(
        self,
        user_id: str,
        plan_type: str,
        payment_method: str,
        payment_token: str
    ) -> Dict:
        """Premium satın al"""
        try:
            # Plan bilgilerini al
            plans = {p["id"]: p for p in self.get_plans()}
            plan = plans.get(plan_type)
            
            if not plan:
                raise Exception("Geçersiz plan")
            
            amount = Decimal(str(plan["price"]))
            currency = plan["currency"]
            
            # Mock mode kontrolü
            if self.payment_mode == "mock":
                transaction_id = f"mock_{payment_token}_{datetime.utcnow().timestamp()}"
            else:
                # Gerçek payment gateway
                if payment_method == "stripe":
                    transaction_id = await self._process_stripe_payment(payment_token, amount)
                elif payment_method == "iyzico":
                    transaction_id = await self._process_iyzico_payment(payment_token, amount)
                else:
                    raise Exception(f"Payment method {payment_method} not implemented")
            
            # Süre hesapla
            now = datetime.utcnow()
            if plan_type == "monthly":
                expires_at = now + timedelta(days=30)
            elif plan_type == "yearly":
                expires_at = now + timedelta(days=365)
            elif plan_type == "lifetime":
                expires_at = now + timedelta(days=365 * 100)  # 100 yıl
            else:
                expires_at = now + timedelta(days=30)
            
            # Purchase kaydı oluştur
            purchase_data = {
                "user_id": user_id,
                "plan_type": plan_type,
                "amount": float(amount),
                "currency": currency,
                "payment_method": payment_method,
                "transaction_id": transaction_id,
                "starts_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "status": "active"
            }
            
            result = self.supabase.table("premium_purchases").insert(
                purchase_data
            ).execute()
            
            if not result.data or len(result.data) == 0:
                raise Exception("Purchase kaydı oluşturulamadı")
            
            purchase = result.data[0]
            
            # User'ı premium yap
            self.supabase.table("users").update({
                "subscription_type": "premium",
                "premium_expires_at": expires_at.isoformat()
            }).eq("id", user_id).execute()
            
            return {
                "purchase_id": purchase.get("id"),
                "plan_type": plan_type,
                "amount": float(amount),
                "currency": currency,
                "payment_method": payment_method,
                "transaction_id": transaction_id,
                "starts_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "status": "active",
                "invoice_url": f"https://billio.app/invoices/{purchase.get('id')}.pdf",
                "created_at": purchase.get("created_at")
            }
            
        except Exception as e:
            raise Exception(f"Purchase error: {str(e)}")
    
    async def verify_payment(
        self,
        user_id: str,
        transaction_id: str,
        payment_method: str
    ) -> Dict:
        """Ödemeyi doğrula"""
        try:
            # Database'de kontrol et
            result = self.supabase.table("premium_purchases").select("*").eq(
                "transaction_id", transaction_id
            ).eq("user_id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return {
                    "verified": True,
                    "purchase": result.data[0]
                }
            
            # TODO: Payment gateway'den kontrol et
            
            return {
                "verified": False,
                "message": "Transaction bulunamadı"
            }
            
        except Exception as e:
            raise Exception(f"Verify error: {str(e)}")
    
    async def get_invoices(self, user_id: str) -> Dict:
        """Faturaları getir"""
        try:
            result = self.supabase.table("premium_purchases").select("*").eq(
                "user_id", user_id
            ).order("created_at", desc=True).execute()
            
            purchases = result.data if result.data else []
            
            invoices = []
            total_spent = Decimal(0)
            
            for purchase in purchases:
                amount = Decimal(str(purchase.get("amount", 0)))
                total_spent += amount
                
                invoices.append({
                    "id": purchase.get("id"),
                    "purchase_id": purchase.get("id"),
                    "plan_type": purchase.get("plan_type"),
                    "amount": float(amount),
                    "currency": purchase.get("currency", "TRY"),
                    "payment_method": purchase.get("payment_method"),
                    "status": "paid" if purchase.get("status") == "active" else purchase.get("status"),
                    "invoice_url": f"https://billio.app/invoices/{purchase.get('id')}.pdf",
                    "created_at": purchase.get("created_at")
                })
            
            return {
                "invoices": invoices,
                "total_spent": float(total_spent),
                "currency": "TRY"
            }
            
        except Exception as e:
            raise Exception(f"Get invoices error: {str(e)}")
    
    async def cancel(
        self,
        user_id: str,
        cancellation_reason: str,
        feedback: Optional[str] = None
    ) -> Dict:
        """Premium iptal et"""
        try:
            # Aktif premium var mı?
            user_result = self.supabase.table("users").select(
                "subscription_type, premium_expires_at"
            ).eq("id", user_id).execute()
            
            if not user_result.data or len(user_result.data) == 0:
                raise Exception("Kullanıcı bulunamadı")
            
            user = user_result.data[0]
            
            if user.get("subscription_type") != "premium":
                raise Exception("Aktif premium abonelik bulunamadı")
            
            expires_at = user.get("premium_expires_at")
            
            # Purchase'ı cancelled yap
            self.supabase.table("premium_purchases").update({
                "status": "cancelled"
            }).eq("user_id", user_id).eq("status", "active").execute()
            
            # TODO: Feedback'i kaydet (ayrı tablo olabilir)
            
            return {
                "cancelled_at": datetime.utcnow().isoformat(),
                "access_until": expires_at,
                "refund_eligible": False,
                "refund_policy": "Yıllık planlar iptal edildiğinde kalan süre için erişim devam eder"
            }
            
        except Exception as e:
            raise Exception(f"Cancel error: {str(e)}")
    
    async def reactivate(self, user_id: str) -> Dict:
        """Premium'u yeniden aktif et"""
        try:
            # İptal edilmiş purchase var mı?
            result = self.supabase.table("premium_purchases").select("*").eq(
                "user_id", user_id
            ).eq("status", "cancelled").order("created_at", desc=True).limit(1).execute()
            
            if not result.data or len(result.data) == 0:
                raise Exception("İptal edilmiş premium bulunamadı")
            
            purchase = result.data[0]
            expires_at = purchase.get("expires_at")
            
            # Reactivate
            self.supabase.table("premium_purchases").update({
                "status": "active"
            }).eq("id", purchase.get("id")).execute()
            
            # User'ı güncelle
            self.supabase.table("users").update({
                "subscription_type": "premium",
                "premium_expires_at": expires_at
            }).eq("id", user_id).execute()
            
            return {
                "plan_type": purchase.get("plan_type"),
                "auto_renewal": True,
                "expires_at": expires_at,
                "reactivated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Reactivate error: {str(e)}")
    
    async def process_webhook(
        self,
        webhook_type: str,
        raw_body: bytes,
        signature: Optional[str] = None
    ) -> Dict:
        """Webhook işle (Stripe/Iyzico) - imza doğrulama"""
        try:
            if webhook_type == "stripe":
                endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
                if not endpoint_secret:
                    raise Exception("Stripe webhook secret eksik")
                if not signature:
                    raise Exception("Stripe signature header eksik")
                if stripe is None:
                    raise Exception("Stripe SDK yüklü değil")
                # Stripe imza doğrulaması (raw body gerekli)
                try:
                    event = stripe.Webhook.construct_event(
                        payload=raw_body.decode("utf-8"),
                        sig_header=signature,
                        secret=endpoint_secret
                    )
                except Exception:
                    raise Exception("Stripe webhook imzası doğrulanamadı")
                event_type = event.get("type")
                data_object = event.get("data", {}).get("object", {})
                # Not: İşleme mantığı TODO, şimdilik doğrulama ve temel bilgi döner
                return {
                    "received": True,
                    "webhook_type": "stripe",
                    "event_type": event_type,
                    "object_id": data_object.get("id")
                }
            elif webhook_type == "iyzico":
                secret = os.getenv("IYZICO_SECRET_KEY") or os.getenv("IYZICO_WEBHOOK_SECRET")
                if not secret:
                    raise Exception("Iyzico secret eksik")
                if not signature:
                    raise Exception("Iyzico signature header eksik")
                computed_sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(computed_sig, signature):
                    raise Exception("Iyzico webhook imzası doğrulanamadı")
                try:
                    payload_json = json.loads(raw_body.decode("utf-8"))
                except Exception:
                    payload_json = {}
                event_type = payload_json.get("event_type") or payload_json.get("event") or "unknown"
                return {
                    "received": True,
                    "webhook_type": "iyzico",
                    "event_type": event_type
                }
            else:
                raise Exception("Bilinmeyen webhook tipi")
        except Exception as exc:
            raise Exception("Webhook processing failed") from exc
    
    # Private helpers
    async def _process_stripe_payment(self, payment_token: str, amount: Decimal) -> str:
        """Stripe ödeme işle (TODO)"""
        # TODO: Stripe API entegrasyonu
        raise Exception("Stripe payment not implemented yet")
    
    async def _process_iyzico_payment(self, payment_token: str, amount: Decimal) -> str:
        """Iyzico ödeme işle (TODO)"""
        # TODO: Iyzico API entegrasyonu
        raise Exception("Iyzico payment not implemented yet")

# Singleton instance
premium_service = PremiumService()
