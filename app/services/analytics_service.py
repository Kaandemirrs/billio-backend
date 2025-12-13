from app.core.supabase import get_supabase_admin_client
from typing import Dict, List
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict

class AnalyticsService:
    """Analytics service"""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
    
    async def get_summary(
        self,
        user_id: str,
        period: str = "monthly",
        currency: str = "TRY"
    ) -> Dict:
        """
        Genel harcama özeti
        
        Args:
            user_id: User UUID
            period: Dönem (monthly, yearly)
            currency: Para birimi
            
        Returns:
            Summary data
        """
        try:
            # Bu ay başlangıç
            now = datetime.utcnow()
            current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Geçen ay başlangıç
            if current_month_start.month == 1:
                previous_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
            else:
                previous_month_start = current_month_start.replace(month=current_month_start.month - 1)
            
            # Bu ay abonelikleri
            current_subs = await self._get_active_subscriptions(
                user_id, current_month_start, currency
            )
            
            # Geçen ay abonelikleri
            previous_subs = await self._get_active_subscriptions(
                user_id, previous_month_start, currency
            )
            
            # Hesaplamalar
            current_total = self._calculate_monthly_total(current_subs)
            previous_total = self._calculate_monthly_total(previous_subs)
            
            # Kategori breakdown
            categories = self._group_by_category(current_subs)
            
            # Karşılaştırma
            difference = current_total - previous_total
            percentage_change = (difference / previous_total * 100) if previous_total > 0 else 0
            trend = "up" if difference > 0 else "down" if difference < 0 else "stable"
            
            # Yıllık projeksiyon
            yearly_total = current_total * 12
            
            # Top subscriptions
            top_subs = self._get_top_subscriptions(current_subs, current_total)
            
            return {
                "current_month": {
                    "total": float(current_total),
                    "currency": currency,
                    "subscription_count": len(current_subs),
                    "categories": {k: float(v) for k, v in categories.items()}
                },
                "comparison": {
                    "previous_month": float(previous_total),
                    "difference": float(difference),
                    "percentage_change": round(float(percentage_change), 2),
                    "trend": trend
                },
                "yearly_projection": {
                    "total": float(yearly_total),
                    "average_monthly": float(current_total)
                },
                "top_subscriptions": top_subs
            }
            
        except Exception as e:
            raise Exception(f"Analytics error: {str(e)}")
    
    async def get_trends(
        self,
        user_id: str,
        months: int = 12
    ) -> Dict:
        """
        Harcama trendleri (son N ay)
        
        Args:
            user_id: User UUID
            months: Kaç ay geriye
            
        Returns:
            Trends data
        """
        try:
            # Son N ay
            monthly_data = []
            now = datetime.utcnow()
            
            for i in range(months, 0, -1):
                # Ay başlangıcı
                if now.month - i + 1 <= 0:
                    month_start = now.replace(
                        year=now.year - 1,
                        month=12 + (now.month - i + 1),
                        day=1,
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0
                    )
                else:
                    month_start = now.replace(
                        month=now.month - i + 1,
                        day=1,
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0
                    )
                
                # Abonelikleri al
                subs = await self._get_active_subscriptions(user_id, month_start, "TRY")
                total = self._calculate_monthly_total(subs)
                
                monthly_data.append({
                    "month": month_start.strftime("%Y-%m"),
                    "total": float(total),
                    "subscription_count": len(subs)
                })
            
            # Kategori breakdown (tüm zamanlar)
            all_subs = await self._get_all_subscriptions(user_id)
            category_breakdown = self._calculate_category_trends(all_subs)
            
            return {
                "monthly_trends": monthly_data,
                "category_breakdown": category_breakdown
            }
            
        except Exception as e:
            raise Exception(f"Trends error: {str(e)}")
    
    async def _get_active_subscriptions(
        self,
        user_id: str,
        start_date: datetime,
        currency: str = "TRY"
    ) -> List[Dict]:
        """Aktif abonelikleri getir"""
        result = self.supabase.table("subscriptions").select("*").eq(
            "user_id", user_id
        ).eq("is_active", True).lte("start_date", start_date.date().isoformat()).execute()
        
        # Currency filter (opsiyonel)
        subs = result.data if result.data else []
        return [s for s in subs if s.get("currency") == currency]
    
    async def _get_all_subscriptions(self, user_id: str) -> List[Dict]:
        """Tüm abonelikleri getir"""
        result = self.supabase.table("subscriptions").select("*").eq(
            "user_id", user_id
        ).execute()
        
        return result.data if result.data else []
    
    def _calculate_monthly_total(self, subscriptions: List[Dict]) -> Decimal:
        """Aylık toplam hesapla"""
        total = Decimal(0)
        
        for sub in subscriptions:
            amount = Decimal(str(sub.get("amount", 0)))
            cycle = sub.get("billing_cycle", "monthly")
            
            # Aylık tutara çevir
            if cycle == "daily":
                total += amount * 30
            elif cycle == "weekly":
                total += amount * 4
            elif cycle == "monthly":
                total += amount
            elif cycle == "yearly":
                total += amount / 12
        
        return total
    
    def _group_by_category(self, subscriptions: List[Dict]) -> Dict[str, Decimal]:
        """Kategoriye göre grupla"""
        categories = defaultdict(lambda: Decimal(0))
        
        for sub in subscriptions:
            category = sub.get("category", "other")
            amount = Decimal(str(sub.get("amount", 0)))
            cycle = sub.get("billing_cycle", "monthly")
            
            # Aylık tutara çevir
            if cycle == "daily":
                monthly_amount = amount * 30
            elif cycle == "weekly":
                monthly_amount = amount * 4
            elif cycle == "monthly":
                monthly_amount = amount
            elif cycle == "yearly":
                monthly_amount = amount / 12
            else:
                monthly_amount = amount
            
            categories[category] += monthly_amount
        
        return dict(categories)
    
    def _get_top_subscriptions(
        self,
        subscriptions: List[Dict],
        total: Decimal
    ) -> List[Dict]:
        """En yüksek harcamaları bul"""
        if total == 0:
            return []
        
        # Aylık tutarlara çevir
        subs_with_monthly = []
        for sub in subscriptions:
            amount = Decimal(str(sub.get("amount", 0)))
            cycle = sub.get("billing_cycle", "monthly")
            
            if cycle == "daily":
                monthly = amount * 30
            elif cycle == "weekly":
                monthly = amount * 4
            elif cycle == "monthly":
                monthly = amount
            elif cycle == "yearly":
                monthly = amount / 12
            else:
                monthly = amount
            
            subs_with_monthly.append({
                "name": sub.get("name"),
                "monthly_amount": monthly
            })
        
        # Sırala
        sorted_subs = sorted(subs_with_monthly, key=lambda x: x["monthly_amount"], reverse=True)
        
        # Top 5
        top = []
        for sub in sorted_subs[:5]:
            percentage = (sub["monthly_amount"] / total * 100) if total > 0 else 0
            top.append({
                "name": sub["name"],
                "amount": float(sub["monthly_amount"]),
                "percentage": round(float(percentage), 1)
            })
        
        return top
    
    def _calculate_category_trends(self, subscriptions: List[Dict]) -> Dict:
        """Kategori trendleri hesapla"""
        categories = self._group_by_category(subscriptions)
        total = sum(categories.values())
        
        breakdown = {}
        for category, amount in categories.items():
            percentage = (amount / total * 100) if total > 0 else 0
            
            breakdown[category] = {
                "total": float(amount * 12),  # Yıllık
                "percentage": round(float(percentage), 1),
                "trend": "stable",  # Basitleştirilmiş
                "change": 0.0
            }
        
        return breakdown

# Singleton instance
analytics_service = AnalyticsService()