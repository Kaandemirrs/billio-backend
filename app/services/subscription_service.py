from app.core.supabase import get_supabase_admin_client
from typing import Optional, List, Dict
from decimal import Decimal
from datetime import date

class SubscriptionService:
    """Subscription service"""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
    
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
                "*, predefined_bills(display_name,icon_name,primary_color,secondary_color)", count="exact"
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
            
            # Summary hesapla
            summary = await self._calculate_summary(user_id)
            
            # Pagination
            total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
            
            return {
                "subscriptions": subscriptions,
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
                amount = Decimal(str(sub.get("amount", 0)))
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
                "*, predefined_bills(display_name,icon_name,primary_color,secondary_color)"
            ).eq(
                "id", subscription_id
            ).eq("user_id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
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
            # user_id ekle
            subscription_data["user_id"] = user_id
            
            # Decimal'i float'a çevir
            if "amount" in subscription_data:
                subscription_data["amount"] = float(subscription_data["amount"])
            
            # Date'i string'e çevir
            if "start_date" in subscription_data:
                subscription_data["start_date"] = str(subscription_data["start_date"])
            
            # Predefined bill eşleştirme (display_name ilike name)
            bill = None
            try:
                bill_res = self.supabase.table("predefined_bills").select("*").ilike(
                    "display_name", subscription_data.get("name")
                ).limit(1).execute()
                bill = bill_res.data[0] if bill_res.data else None
            except Exception:
                bill = None
            
            if bill:
                subscription_data["predefined_bill_id"] = bill.get("id")
                if not subscription_data.get("category"):
                    subscription_data["category"] = bill.get("category") or "other"
                if not subscription_data.get("color"):
                    subscription_data["color"] = bill.get("primary_color") or "#6366f1"
            
            # Insert
            result = self.supabase.table("subscriptions").insert(
                subscription_data
            ).execute()
            
            if result.data and len(result.data) > 0:
                inserted_id = result.data[0].get("id")
                # Join ile geri döndür
                joined = self.supabase.table("subscriptions").select(
                    "*, predefined_bills(*)"
                ).eq("id", inserted_id).execute()
                if joined.data and len(joined.data) > 0:
                    return joined.data[0]
                return result.data[0]
            
            raise Exception("Abonelik oluşturulamadı")
            
        except Exception as e:
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
                "*, predefined_bills(display_name,icon_name,primary_color,secondary_color)"
            ).eq(
                "id", subscription_id
            ).eq("user_id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
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