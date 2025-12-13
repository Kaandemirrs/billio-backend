from typing import List
from app.core.supabase import get_supabase_admin_client


class AnalysisContextService:
    """RAG bağlamını tek bir metin bloğu olarak derleyen servis."""

    def __init__(self):
        self.supabase = get_supabase_admin_client()

    async def get_comprehensive_analysis_context(self, user_id: str) -> str:
        """
        Kullanıcının aktif abonelikleri ve servis planlarındaki AI önbellek fiyatlarını
        toplayıp Gemini için yapılandırılmış bir metin (context_text) üretir.

        Format:
        [USER_SUBSCRIPTIONS]
        - name: NAME | amount: AMOUNT CURRENCY | cycle: BILLING_CYCLE

        [AI_CACHED_PRICES]
        - plan: PLAN_NAME | price: CACHED_PRICE CURRENCY | updated: LAST_UPDATED_AI
        """
        # 1) Aktif abonelikleri çek
        subs_result = self.supabase.table("subscriptions").select(
            "name, amount, currency, billing_cycle, is_active"
        ).eq("user_id", user_id).eq("is_active", True).execute()

        subscriptions = subs_result.data or []

        # 2) Servis planlarındaki AI önbellek fiyatlarını çek
        plans_result = self.supabase.table("service_plans").select(
            "plan_name, cached_price, currency, last_updated_ai"
        ).execute()

        service_plans = plans_result.data or []

        # 3) Metin bloklarını oluştur
        lines: List[str] = []
        lines.append("[USER_SUBSCRIPTIONS]")
        if subscriptions:
            for s in subscriptions:
                name = s.get("name")
                amount = s.get("amount")
                currency = s.get("currency") or "TRY"
                cycle = s.get("billing_cycle") or "monthly"
                lines.append(f"- name: {name} | amount: {amount} {currency} | cycle: {cycle}")
        else:
            lines.append("- none")

        lines.append("")
        lines.append("[AI_CACHED_PRICES]")
        if service_plans:
            for sp in service_plans:
                plan_name = sp.get("plan_name")
                cached_price = sp.get("cached_price")
                currency = sp.get("currency") or "TRY"
                updated = sp.get("last_updated_ai")
                lines.append(
                    f"- plan: {plan_name} | price: {cached_price} {currency} | updated: {updated}"
                )
        else:
            lines.append("- none")

        lines.append("")
        lines.append("[NOTES]")
        lines.append(
            "- Amaç: Kullanıcıya tasarruf ve kârlılık odaklı öneriler üretmek."
        )

        context_text = "\n".join(lines)
        return context_text


# Singleton instance
analysis_context_service = AnalysisContextService()