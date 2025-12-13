from app.core.supabase import get_supabase_client
from datetime import datetime
from typing import Optional

class AuthService:
    """Authentication service"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def sync_user(
        self,
        firebase_uid: str,
        email: str,
        full_name: Optional[str] = None
    ) -> dict:
        """
        Firebase'den gelen user'ı Supabase'e senkronize et
        
        Args:
            firebase_uid: Firebase UID
            email: User email
            full_name: User full name (optional)
            
        Returns:
            dict: {user: dict, is_new_user: bool}
        """
        try:
            # User var mı kontrol et
            result = self.supabase.table("users").select("*").eq(
                "firebase_uid", firebase_uid
            ).execute()
            
            if result.data and len(result.data) > 0:
                # User var, last_login_at güncelle
                existing_user = result.data[0]
                
                update_result = self.supabase.table("users").update({
                    "last_login_at": datetime.utcnow().isoformat()
                }).eq("firebase_uid", firebase_uid).execute()
                
                # Güncel user'ı al
                updated_user = update_result.data[0] if update_result.data else existing_user
                
                return {
                    "user": self._format_user(updated_user),
                    "is_new_user": False
                }
            else:
                # User yok, yeni oluştur
                new_user_data = {
                    "firebase_uid": firebase_uid,
                    "email": email,
                    "full_name": full_name,
                    "last_login_at": datetime.utcnow().isoformat()
                }
                
                insert_result = self.supabase.table("users").insert(
                    new_user_data
                ).execute()
                
                new_user = insert_result.data[0]
                
                return {
                    "user": self._format_user(new_user),
                    "is_new_user": True
                }
                
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")
    
    def _format_user(self, user_data: dict) -> dict:
        """
        Supabase'den gelen user verisini formatla
        """
        return {
            "id": user_data.get("id"),
            "firebase_uid": user_data.get("firebase_uid"),
            "email": user_data.get("email"),
            "full_name": user_data.get("full_name"),
            "phone_number": user_data.get("phone_number"),
            "phone_verified": user_data.get("phone_verified", False),
            "subscription_type": user_data.get("subscription_type", "free"),
            "premium_expires_at": user_data.get("premium_expires_at"),
            "settings": {
                "preferred_currency": user_data.get("preferred_currency", "TRY"),
                "preferred_language": user_data.get("preferred_language", "tr"),
                "notification_enabled": user_data.get("notification_enabled", True),
                "reminder_days": user_data.get("reminder_days", 3),
                "theme": user_data.get("theme", "light")
            },
            "created_at": user_data.get("created_at"),
            "last_login_at": user_data.get("last_login_at")
        }

# Singleton instance
auth_service = AuthService()