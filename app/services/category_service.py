from typing import List, Dict

class CategoryService:
    """Category service"""
    
    def get_categories(self, language: str = "tr") -> List[Dict]:
        """Kategorileri getir"""
        categories = [
            {
                "id": "entertainment",
                "name": "Eğlence",
                "name_en": "Entertainment",
                "icon": "🎬",
                "color": "#E50914",
                "description": "Film, müzik, oyun platformları"
            },
            {
                "id": "utilities",
                "name": "Faturalar",
                "name_en": "Utilities",
                "icon": "⚡",
                "color": "#FFA500",
                "description": "Elektrik, su, internet, telefon"
            },
            {
                "id": "productivity",
                "name": "Verimlilik",
                "name_en": "Productivity",
                "icon": "📊",
                "color": "#4CAF50",
                "description": "Çalışma araçları, cloud storage"
            },
            {
                "id": "health",
                "name": "Sağlık",
                "name_en": "Health",
                "icon": "❤️",
                "color": "#FF5722",
                "description": "Fitness, sağlık hizmetleri"
            },
            {
                "id": "finance",
                "name": "Finans",
                "name_en": "Finance",
                "icon": "💰",
                "color": "#2196F3",
                "description": "Bankacılık, yatırım platformları"
            },
            {
                "id": "education",
                "name": "Eğitim",
                "name_en": "Education",
                "icon": "📚",
                "color": "#9C27B0",
                "description": "Online kurslar, eğitim platformları"
            },
            {
                "id": "other",
                "name": "Diğer",
                "name_en": "Other",
                "icon": "📦",
                "color": "#607D8B",
                "description": "Diğer abonelikler"
            }
        ]
        
        return categories
    
    async def get_category_stats(
        self,
        user_id: str,
        subscription_service
    ) -> Dict:
        """Kullanıcının kategori istatistikleri"""
        from decimal import Decimal
        from collections import defaultdict
        
        # Subscription service'den abonelikleri al
        result = await subscription_service.get_subscriptions(
            user_id=user_id,
            page=1,
            limit=1000  # Tümünü al
        )
        
        subscriptions = result.get("subscriptions", [])
        
        # Kategorilere göre grupla
        category_data = defaultdict(lambda: {"count": 0, "total": Decimal(0)})
        
        for sub in subscriptions:
            if not sub.get("is_active"):
                continue
            
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
            
            category_data[category]["count"] += 1
            category_data[category]["total"] += monthly_amount
        
        # Toplam hesapla
        total_monthly = sum(data["total"] for data in category_data.values())
        
        # Format
        categories = self.get_categories()
        category_map = {c["id"]: c for c in categories}
        
        stats = []
        for cat_id, data in category_data.items():
            cat_info = category_map.get(cat_id, {"name": cat_id})
            percentage = (data["total"] / total_monthly * 100) if total_monthly > 0 else 0
            
            stats.append({
                "id": cat_id,
                "name": cat_info.get("name", cat_id),
                "subscription_count": data["count"],
                "total_monthly": float(data["total"]),
                "percentage": round(float(percentage), 1)
            })
        
        # Sırala (en yüksekten düşüğe)
        stats.sort(key=lambda x: x["total_monthly"], reverse=True)
        
        return {
            "categories": stats,
            "total_monthly": float(total_monthly),
            "currency": "TRY"
        }

# Singleton instance
category_service = CategoryService()