from app.core.supabase import get_supabase_admin_client
from typing import Dict, List, Optional
from decimal import Decimal
import random
import json

class AIService:
    """AI Analysis service"""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
    
    async def analyze_subscription(
        self,
        user_id: str,
        subscription_id: str
    ) -> Dict:
        """
        Tek bir aboneliği analiz et (Mock AI)
        
        Args:
            user_id: User UUID
            subscription_id: Subscription UUID
            
        Returns:
            Analysis data
        """
        try:
            # Subscription getir
            sub_result = self.supabase.table("subscriptions").select("*").eq(
                "id", subscription_id
            ).eq("user_id", user_id).execute()
            
            if not sub_result.data or len(sub_result.data) == 0:
                raise Exception("Abonelik bulunamadı")
            
            subscription = sub_result.data[0]
            
            # Mock AI Analysis
            suggestions = self._generate_mock_suggestions(subscription)
            analysis_details = self._generate_mock_details(subscription)
            
            # Veritabanına kaydet
            analysis_data = {
                "user_id": user_id,
                "subscription_id": subscription_id,
                "current_plan": subscription.get("name"),
                "current_amount": float(subscription.get("amount")),
                "suggested_plan": suggestions[0].get("suggested_plan") if suggestions else None,
                "suggested_amount": suggestions[0].get("suggested_amount") if suggestions else None,
                "alternative_service": suggestions[0].get("alternative_service") if suggestions else None,
                "potential_monthly_savings": suggestions[0].get("potential_monthly_savings") if suggestions else None,
                "potential_yearly_savings": suggestions[0].get("potential_yearly_savings") if suggestions else None,
                "analysis_details": json.dumps(analysis_details),
                "confidence_score": suggestions[0].get("confidence_score") if suggestions else 0.5
            }
            
            result = self.supabase.table("ai_analysis").insert(
                analysis_data
            ).execute()
            
            if result.data and len(result.data) > 0:
                analysis = result.data[0]
                
                return {
                    "id": analysis.get("id"),
                    "subscription_id": subscription_id,
                    "current_plan": analysis.get("current_plan"),
                    "current_amount": float(analysis.get("current_amount")),
                    "suggestions": suggestions,
                    "analysis_details": analysis_details,
                    "created_at": analysis.get("created_at")
                }
            
            raise Exception("Analiz kaydedilemedi")
            
        except Exception as e:
            raise Exception(f"AI analysis error: {str(e)}")
    
    async def get_latest_analysis(
        self,
        user_id: str,
        subscription_id: str
    ) -> Optional[Dict]:
        """Son analizi getir"""
        try:
            result = self.supabase.table("ai_analysis").select("*").eq(
                "user_id", user_id
            ).eq("subscription_id", subscription_id).order(
                "created_at", desc=True
            ).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                analysis = result.data[0]
                
                # Analysis details parse et
                details = json.loads(analysis.get("analysis_details", "{}"))
                
                # Suggestions oluştur
                suggestions = [{
                    "type": "downgrade" if analysis.get("suggested_plan") else "keep",
                    "suggested_plan": analysis.get("suggested_plan"),
                    "suggested_amount": float(analysis.get("suggested_amount")) if analysis.get("suggested_amount") else None,
                    "alternative_service": analysis.get("alternative_service"),
                    "potential_monthly_savings": float(analysis.get("potential_monthly_savings")) if analysis.get("potential_monthly_savings") else None,
                    "potential_yearly_savings": float(analysis.get("potential_yearly_savings")) if analysis.get("potential_yearly_savings") else None,
                    "confidence_score": float(analysis.get("confidence_score", 0.5)),
                    "reason": details.get("recommendation", "")
                }]
                
                return {
                    "id": analysis.get("id"),
                    "subscription_id": subscription_id,
                    "current_plan": analysis.get("current_plan"),
                    "current_amount": float(analysis.get("current_amount")),
                    "suggestions": suggestions,
                    "analysis_details": details,
                    "created_at": analysis.get("created_at")
                }
            
            return None
            
        except Exception as e:
            raise Exception(f"Get analysis error: {str(e)}")
    
    async def bulk_analyze(
        self,
        user_id: str
    ) -> Dict:
        """Tüm abonelikleri toplu analiz et"""
        try:
            # Aktif abonelikleri al
            subs_result = self.supabase.table("subscriptions").select("*").eq(
                "user_id", user_id
            ).eq("is_active", True).execute()
            
            subscriptions = subs_result.data if subs_result.data else []
            
            if not subscriptions:
                raise Exception("Aktif abonelik bulunamadı")
            
            recommendations = []
            total_savings = Decimal(0)
            summary = {"keep": 0, "downgrade": 0, "cancel": 0, "alternative": 0}
            
            # Her abonelik için analiz
            for sub in subscriptions:
                action, savings = self._mock_bulk_decision(sub)
                
                summary[action] += 1
                if savings:
                    total_savings += Decimal(str(savings))
                
                recommendations.append({
                    "subscription_id": sub.get("id"),
                    "subscription_name": sub.get("name"),
                    "action": action,
                    "potential_savings": float(savings) if savings else None,
                    "priority": "high" if savings and savings > 50 else "low",
                    "reason": self._get_action_reason(action)
                })
            
            # Bulk analysis ID (ilk subscription'ın analysis'i)
            analysis_id = str(subscriptions[0].get("id")) + "-bulk"
            
            return {
                "total_analyzed": len(subscriptions),
                "analysis_id": analysis_id,
                "total_potential_savings": {
                    "monthly": float(total_savings),
                    "yearly": float(total_savings * 12),
                    "currency": "TRY"
                },
                "recommendations": recommendations,
                "summary": summary,
                "created_at": "2025-10-16T18:00:00Z"
            }
            
        except Exception as e:
            raise Exception(f"Bulk analysis error: {str(e)}")
    
    async def apply_suggestion(
        self,
        user_id: str,
        analysis_id: str
    ) -> Dict:
        """AI önerisini uygula"""
        try:
            # Analysis getir
            analysis_result = self.supabase.table("ai_analysis").select("*").eq(
                "id", analysis_id
            ).eq("user_id", user_id).execute()
            
            if not analysis_result.data or len(analysis_result.data) == 0:
                raise Exception("Analiz bulunamadı")
            
            analysis = analysis_result.data[0]
            
            # Zaten uygulanmış mı?
            if analysis.get("is_applied"):
                raise Exception("Bu öneri zaten uygulanmış")
            
            # Subscription'ı güncelle
            subscription_id = analysis.get("subscription_id")
            new_amount = analysis.get("suggested_amount")
            
            if new_amount:
                self.supabase.table("subscriptions").update({
                    "amount": float(new_amount)
                }).eq("id", subscription_id).execute()
            
            # Analysis'i güncelle
            from datetime import datetime
            self.supabase.table("ai_analysis").update({
                "is_applied": True,
                "applied_at": datetime.utcnow().isoformat()
            }).eq("id", analysis_id).execute()
            
            old_amount = Decimal(str(analysis.get("current_amount")))
            new_amount_dec = Decimal(str(new_amount))
            savings = old_amount - new_amount_dec
            
            return {
                "analysis_id": analysis_id,
                "subscription_id": subscription_id,
                "old_amount": float(old_amount),
                "new_amount": float(new_amount_dec),
                "monthly_savings": float(savings),
                "is_applied": True,
                "applied_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Apply suggestion error: {str(e)}")
    
    async def add_feedback(
        self,
        user_id: str,
        analysis_id: str,
        feedback: str,
        comment: Optional[str] = None
    ) -> Dict:
        """Geri bildirim ekle"""
        try:
            from datetime import datetime
            
            # Analysis var mı?
            check = self.supabase.table("ai_analysis").select("id").eq(
                "id", analysis_id
            ).eq("user_id", user_id).execute()
            
            if not check.data or len(check.data) == 0:
                raise Exception("Analiz bulunamadı")
            
            # Feedback güncelle
            self.supabase.table("ai_analysis").update({
                "user_feedback": feedback
            }).eq("id", analysis_id).execute()
            
            return {
                "analysis_id": analysis_id,
                "user_feedback": feedback,
                "feedback_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Feedback error: {str(e)}")
    
    async def get_history(
        self,
        user_id: str,
        is_applied: Optional[bool] = None,
        limit: int = 10,
        page: int = 1
    ) -> Dict:
        """Geçmiş analizleri getir"""
        try:
            query = self.supabase.table("ai_analysis").select(
                "*, subscriptions(name)", count="exact"
            ).eq("user_id", user_id).order("created_at", desc=True)
            
            if is_applied is not None:
                query = query.eq("is_applied", is_applied)
            
            # Pagination
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)
            
            result = query.execute()
            
            analyses = result.data if result.data else []
            total_items = result.count if result.count else 0
            
            # Summary hesapla
            summary = await self._calculate_history_summary(user_id)
            
            # Format
            history_items = []
            for analysis in analyses:
                sub_name = analysis.get("subscriptions", {}).get("name", "Unknown")
                
                history_items.append({
                    "id": analysis.get("id"),
                    "subscription_name": sub_name,
                    "suggestion_type": "downgrade" if analysis.get("suggested_plan") else "keep",
                    "potential_savings": float(analysis.get("potential_monthly_savings")) if analysis.get("potential_monthly_savings") else None,
                    "is_applied": analysis.get("is_applied", False),
                    "applied_at": analysis.get("applied_at"),
                    "user_feedback": analysis.get("user_feedback"),
                    "created_at": analysis.get("created_at")
                })
            
            total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
            
            return {
                "analyses": history_items,
                "summary": summary,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages,
                    "total_items": total_items
                }
            }
            
        except Exception as e:
            raise Exception(f"History error: {str(e)}")
    
    async def delete_analysis(
        self,
        user_id: str,
        analysis_id: str
    ) -> bool:
        """Analizi sil"""
        try:
            self.supabase.table("ai_analysis").delete().eq(
                "id", analysis_id
            ).eq("user_id", user_id).execute()
            
            return True
            
        except Exception as e:
            raise Exception(f"Delete error: {str(e)}")
    
    async def get_stats(self, user_id: str) -> Dict:
        """AI kullanım istatistikleri"""
        try:
            result = self.supabase.table("ai_analysis").select("*").eq(
                "user_id", user_id
            ).execute()
            
            analyses = result.data if result.data else []
            
            total_analyses = len(analyses)
            applied = len([a for a in analyses if a.get("is_applied")])
            
            # Toplam tasarruf
            total_savings = sum([
                Decimal(str(a.get("potential_monthly_savings", 0)))
                for a in analyses if a.get("is_applied")
            ])
            
            # Ortalama confidence
            confidences = [float(a.get("confidence_score", 0.5)) for a in analyses]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Feedback distribution
            feedback_dist = {"helpful": 0, "not_helpful": 0, "wrong": 0, "no_feedback": 0}
            for a in analyses:
                fb = a.get("user_feedback")
                if fb:
                    feedback_dist[fb] += 1
                else:
                    feedback_dist["no_feedback"] += 1
            
            return {
                "total_analyses": total_analyses,
                "applied_suggestions": applied,
                "total_savings": float(total_savings),
                "average_confidence": round(avg_confidence, 2),
                "feedback_distribution": feedback_dist
            }
            
        except Exception as e:
            raise Exception(f"Stats error: {str(e)}")
    
    # Private helpers
    def _generate_mock_suggestions(self, subscription: Dict) -> List[Dict]:
        """Mock AI önerileri oluştur"""
        current_amount = Decimal(str(subscription.get("amount", 0)))
        name = subscription.get("name", "")
        
        # Mock downgrade önerisi
        downgrade_amount = current_amount * Decimal("0.8")
        savings = current_amount - downgrade_amount
        
        return [{
            "type": "downgrade",
            "suggested_plan": f"{name} Basic",
            "suggested_amount": float(downgrade_amount),
            "alternative_service": None,
            "potential_monthly_savings": float(savings),
            "potential_yearly_savings": float(savings * 12),
            "confidence_score": round(random.uniform(0.7, 0.95), 2),
            "reason": "Kullanım verilerinize göre daha ekonomik bir plan öneriyoruz."
        }]
    
    def _generate_mock_details(self, subscription: Dict) -> Dict:
        """Mock analiz detayları"""
        return {
            "usage_pattern": random.choice(["low", "medium", "high"]),
            "recommendation": "Daha ekonomik bir plan kullanabilirsiniz",
            "priority": random.choice(["low", "medium", "high"])
        }
    
    def _mock_bulk_decision(self, subscription: Dict) -> tuple:
        """Mock bulk karar"""
        actions = ["keep", "downgrade", "cancel"]
        weights = [0.5, 0.3, 0.2]
        action = random.choices(actions, weights)[0]
        
        if action == "downgrade":
            savings = float(Decimal(str(subscription.get("amount", 0))) * Decimal("0.2"))
        elif action == "cancel":
            savings = float(subscription.get("amount", 0))
        else:
            savings = None
        
        return action, savings
    
    def _get_action_reason(self, action: str) -> str:
        """Action açıklaması"""
        reasons = {
            "keep": "Optimal plan kullanılıyor",
            "downgrade": "Daha ekonomik plan öneriliyor",
            "cancel": "Kullanım verilerine göre iptal öneriliyor"
        }
        return reasons.get(action, "")
    
    async def _calculate_history_summary(self, user_id: str) -> Dict:
        """Geçmiş özeti hesapla"""
        result = self.supabase.table("ai_analysis").select("*").eq(
            "user_id", user_id
        ).execute()
        
        analyses = result.data if result.data else []
        
        total = len(analyses)
        applied = len([a for a in analyses if a.get("is_applied")])
        
        savings = sum([
            Decimal(str(a.get("potential_monthly_savings", 0)))
            for a in analyses if a.get("is_applied")
        ])
        
        return {
            "total_analyses": total,
            "applied_count": applied,
            "total_savings_realized": float(savings),
            "currency": "TRY"
        }

# Singleton instance
ai_service = AIService()