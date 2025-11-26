from app.core.supabase import get_supabase_admin_client
from typing import Optional, List, Dict
from decimal import Decimal
from datetime import date

class SubscriptionService:
    """Subscription service"""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()

    def _calculate_price_alert_status(self, subscription: Dict) -> str:
        """
        "Senaryo 2: Zam Uyarısı" mantığını hesaplar.
        Hata durumunda sistemi çökertmez, 'none' döner ve hatayı loglar.
        """
        try:
            # 1. Güvenlik Kontrolü: service_plans var mı?
            plans = subscription.get("service_plans")
            if not plans:
                return "none"

            # 2. Fiyat Kontrolü: cached_price var mı?
            cached_price_val = plans.get("cached_price")
            if cached_price_val is None:
                return "none"

            # 3. Dönüşüm (En riskli yer burasıdır)
            # Gelen veriyi önce string'e sonra Decimal'e çevirerek güvenliği artır.
            user_amount = Decimal(str(subscription.get("amount", 0)))
            cached_price = Decimal(str(cached_price_val))

            # 4. Mantık Kontrolü
            if cached_price > 0 and user_amount != cached_price:
                return "update_required"

            return "none"

        except Exception as e:
            # KRİTİK: Hatayı yutma, loga yaz ama sistemi çökertme.
            print(f"⚠️ ALERT CALCULATION ERROR (Sub ID: {subscription.get('id')}): {str(e)}")
            return "none"
    
    async def get_subscriptions(
        self,
        user_id: str,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_by: str = "created_at",
        order: str = "desc",
        page: int = 1,
        limit: int = 20
    ) -> Dict:
        """
        Abonelikleri listele
        
        Args:
            user_id: User UUID
            category: Kategori filtresi
            is_active: Aktiflik filtresi
            sort_by: Sıralama alanı
            order: asc/desc
            page: Sayfa numarası
            limit: Sayfa başına kayıt
            
        Returns:
            Subscriptions, summary, pagination
        """
        try:
            # Query builder
            query = self.supabase.table("subscriptions").select(
                "*, service_plans(*)", count="exact"
            ).eq("user_id", user_id)
            
            # Filters
            if category:
                query = query.eq("category", category)
            
            if is_active is not None:
                query = query.eq("is_active", is_active)
            
            # Sorting
            query = query.order(sort_by, desc=(order == "desc"))
            
            # Pagination
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)
            
            # Execute
            result = query.execute()
            
            subscriptions = result.data if result.data else []
            total_items = result.count if result.count else 0

            # Akıllı Backend: price_alert_status hesapla
            processed_subscriptions = []
            for sub in subscriptions:
                sub["price_alert_status"] = self._calculate_price_alert_status(sub)
                processed_subscriptions.append(sub)
            
            # Summary hesapla
            summary = await self._calculate_summary(user_id)
            
            # Pagination
            total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
            
            return {
                "subscriptions": processed_subscriptions,
                "summary": summary,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages,
                    "total_items": total_items
                }
            }
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")
    
    async def _calculate_summary(self, user_id: str) -> Dict:
        """Abonelik özetini hesapla"""
        try:
            # Aktif abonelikleri al
            result = self.supabase.table("subscriptions").select(
                "amount, billing_cycle, currency, is_active"
            ).eq("user_id", user_id).execute()
            
            if not result.data:
                return {
                    "total_monthly": 0,
                    "total_yearly": 0,
                    "active_count": 0,
                    "inactive_count": 0,
                    "currency": "TRY"
                }
            
            total_monthly = Decimal(0)
            active_count = 0
            inactive_count = 0
            currency = "TRY"
            
            for sub in result.data:
                # amount None olabilir; güvenli dönüşüm uygula
                amount_value = sub.get("amount")
                try:
                    amount = Decimal(str(amount_value)) if amount_value is not None else Decimal(0)
                except Exception:
                    amount = Decimal(0)
                cycle = sub.get("billing_cycle", "monthly")
                is_active = sub.get("is_active", True)
                currency = sub.get("currency", "TRY")
                
                if is_active:
                    active_count += 1
                    # Aylık tutara çevir
                    if cycle == "daily":
                        total_monthly += amount * 30
                    elif cycle == "weekly":
                        total_monthly += amount * 4
                    elif cycle == "monthly":
                        total_monthly += amount
                    elif cycle == "yearly":
                        total_monthly += amount / 12
                else:
                    inactive_count += 1
            
            total_yearly = total_monthly * 12
            
            return {
                "total_monthly": float(total_monthly),
                "total_yearly": float(total_yearly),
                "active_count": active_count,
                "inactive_count": inactive_count,
                "currency": currency
            }
            
        except Exception as e:
            raise Exception(f"Summary calculation error: {str(e)}")
    
    async def get_subscription_by_id(
        self,
        subscription_id: str,
        user_id: str
    ) -> Optional[Dict]:
        """Tek bir aboneliği getir"""
        try:
            result = self.supabase.table("subscriptions").select(
                "*, service_plans(*)"
            ).eq(
                "id", subscription_id
            ).eq("user_id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                subscription = result.data[0]
                subscription["price_alert_status"] = self._calculate_price_alert_status(subscription)
                return subscription
            
            return None
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")
    
    async def create_subscription(
        self,
        user_id: str,
        subscription_data: Dict
    ) -> Dict:
        """Yeni abonelik oluştur"""
        try:
            # 1. HAZIRLIK: Verileri hazırla
            subscription_data["user_id"] = user_id

            if "amount" in subscription_data:
                subscription_data["amount"] = float(subscription_data["amount"])

            if "start_date" in subscription_data:
                subscription_data["start_date"] = str(subscription_data["start_date"])

            # 2. İŞLEM: SADECE INSERT (Karmaşık JOIN yok)
            result = self.supabase.table("subscriptions").insert(
                subscription_data
            ).execute()

            # 3. SONUÇ: Eklenen veriyi güvenli yoldan geri getir
            if result.data and len(result.data) > 0:
                inserted_id = result.data[0].get("id")

                # ZATEN ÇALIŞAN FONKSİYONU KULLANIYORUZ
                created_subscription = await self.get_subscription_by_id(
                    subscription_id=inserted_id,
                    user_id=user_id,
                )

                if created_subscription:
                    return created_subscription

                # Çok düşük ihtimal ama okuma başarısız olursa ham veriyi dön
                return result.data[0]

            raise Exception("Abonelik oluşturulamadı (Veritabanı yanıt vermedi)")

        except Exception as e:
            print(f"CREATE SUBSCRIPTION ERROR: {str(e)}")
            raise Exception(f"Supabase error: {str(e)}")
    
    async def update_subscription(
        self,
        subscription_id: str,
        user_id: str,
        update_data: Dict
    ) -> Optional[Dict]:
        """Aboneliği güncelle"""
        try:
            # Decimal'i float'a çevir
            if "amount" in update_data:
                update_data["amount"] = float(update_data["amount"])
            
            # Date'i string'e çevir
            if "start_date" in update_data:
                update_data["start_date"] = str(update_data["start_date"])
            
            # UPDATE
            self.supabase.table("subscriptions").update(
                update_data
            ).eq("id", subscription_id).eq("user_id", user_id).execute()
            
            # SELECT ile tekrar al (join ile)
            result = self.supabase.table("subscriptions").select(
                "*, service_plans(*)"
            ).eq(
                "id", subscription_id
            ).eq("user_id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                subscription = result.data[0]
                subscription["price_alert_status"] = self._calculate_price_alert_status(subscription)
                return subscription
            
            return None
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")
    
    async def delete_subscription(
        self,
        subscription_id: str,
        user_id: str
    ) -> bool:
        """Aboneliği sil"""
        try:
            self.supabase.table("subscriptions").delete().eq(
                "id", subscription_id
            ).eq("user_id", user_id).execute()
            
            return True
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")
    
    async def toggle_subscription(
        self,
        subscription_id: str,
        user_id: str,
        is_active: bool
    ) -> Optional[Dict]:
        """Abonelik durumunu değiştir"""
        try:
            return await self.update_subscription(
                subscription_id=subscription_id,
                user_id=user_id,
                update_data={"is_active": is_active}
            )
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")

# Singleton instance
subscription_service = SubscriptionService()
