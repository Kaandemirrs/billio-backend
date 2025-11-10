from app.core.supabase import get_supabase_admin_client
from typing import Optional
import secrets
import hashlib

class UserService:
    """User service"""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client() 
    
    async def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[dict]:
        """
        Firebase UID ile user'ı getir
        
        Args:
            firebase_uid: Firebase UID
            
        Returns:
            User data or None
        """
        try:
            result = self.supabase.table("users").select("*").eq(
                "firebase_uid", firebase_uid
            ).execute()
            
            if result.data and len(result.data) > 0:
                return self._format_user(result.data[0])
            
            return None
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")
    
    def _format_user(self, user_data: dict) -> dict:
        """Supabase'den gelen user verisini formatla"""
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
    
    async def update_profile(
        self,
        firebase_uid: str,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Optional[dict]:
        """
        Profil bilgilerini güncelle
        
        Args:
            firebase_uid: Firebase UID
            full_name: Yeni isim
            phone_number: Yeni telefon
            
        Returns:
            Güncellenmiş user
        """
        try:
            # Güncellenecek alanlar
            update_data = {}
            
            if full_name is not None:
                update_data["full_name"] = full_name
            
            if phone_number is not None:
                # Telefon numarası değiştiyse phone_verified'ı false yap
                result = self.supabase.table("users").select("phone_number").eq(
                    "firebase_uid", firebase_uid
                ).execute()
                
                if result.data and len(result.data) > 0:
                    old_phone = result.data[0].get("phone_number")
                    if old_phone != phone_number:
                        update_data["phone_verified"] = False
                
                update_data["phone_number"] = phone_number
            
            if not update_data:
                # Hiçbir şey güncellenmedi, mevcut user'ı döndür
                return await self.get_user_by_firebase_uid(firebase_uid)
            
            # UPDATE yap
            self.supabase.table("users").update(
                update_data
            ).eq("firebase_uid", firebase_uid).execute()
            
            # SELECT ile tekrar al
            user_result = self.supabase.table("users").select("*").eq(
                "firebase_uid", firebase_uid
            ).execute()
            
            if user_result.data and len(user_result.data) > 0:
                return self._format_user(user_result.data[0])
            
            return None
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")
    
    async def delete_account(self, firebase_uid: str) -> bool:
        """
        Hesabı sil (CASCADE DELETE - tüm ilişkili veriler silinir)
        
        Args:
            firebase_uid: Firebase UID
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            result = self.supabase.table("users").delete().eq(
                "firebase_uid", firebase_uid
            ).execute()
            
            return True
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")


    async def request_phone_verification(
        self,
        firebase_uid: str,
        phone_number: str
    ) -> dict:
        """
        SMS doğrulama kodu gönder
        
        Args:
            firebase_uid: Firebase UID
            phone_number: Telefon numarası
            
        Returns:
            dict: Kod bilgileri
        """
        try:
            from datetime import datetime, timedelta
            
            # 6 haneli kod üret (güvenli random)
            verification_code = f"{secrets.randbelow(1_000_000):06d}"
            verification_hash = hashlib.sha256(verification_code.encode("utf-8")).hexdigest()
            
            # 5 dakika sonra expire
            expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            
            # Database'e kaydet
            update_data = {
                "phone_number": phone_number,
                "phone_verification_code": verification_hash,
                "phone_verification_expires_at": expires_at,
                "phone_verified": False  # Henüz doğrulanmadı
            }
            
            self.supabase.table("users").update(
                update_data
            ).eq("firebase_uid", firebase_uid).execute()
            
            # TODO: SMS gönder (Twilio/Netgsm)
            # Hassas verileri loglama
            print(f"📱 SMS doğrulama kodu oluşturuldu (user: {firebase_uid})")
            
            return {
                "expires_at": expires_at,
                "code_sent_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")
    
    async def verify_phone(
        self,
        firebase_uid: str,
        verification_code: str
    ) -> bool:
        """
        SMS kodunu doğrula
        
        Args:
            firebase_uid: Firebase UID
            verification_code: SMS kodu
            
        Returns:
            bool: Doğru mu?
        """
        try:
            from datetime import datetime
            
            # User'ı al
            result = self.supabase.table("users").select(
                "phone_verification_code, phone_verification_expires_at"
            ).eq("firebase_uid", firebase_uid).execute()
            
            if not result.data or len(result.data) == 0:
                raise Exception("Kullanıcı bulunamadı")
            
            user_data = result.data[0]
            stored_code = user_data.get("phone_verification_code")
            expires_at = user_data.get("phone_verification_expires_at")
            
            # Kod yok
            if not stored_code:
                raise Exception("Doğrulama kodu bulunamadı. Önce kod isteyin.")
            
            # Kod yanlış
            provided_hash = hashlib.sha256(verification_code.encode("utf-8")).hexdigest()
            if stored_code != provided_hash:
                raise Exception("Doğrulama kodu hatalı")
            
            # Süre dolmuş
            if expires_at:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.utcnow().replace(tzinfo=expires_datetime.tzinfo) > expires_datetime:
                    raise Exception("Doğrulama kodunun süresi dolmuş")
            
            # Doğrulama başarılı, güncelle
            update_data = {
                "phone_verified": True,
                "phone_verification_code": None,
                "phone_verification_expires_at": None
            }
            
            self.supabase.table("users").update(
                update_data
            ).eq("firebase_uid", firebase_uid).execute()
            
            return True
            
        except Exception as e:
            raise Exception(f"Verification error: {str(e)}")
        


    async def get_settings(self, firebase_uid: str) -> dict:
        """
        Kullanıcı ayarlarını getir
        """
        try:
            result = self.supabase.table("users").select(
                "preferred_currency, preferred_language, notification_enabled, reminder_days, theme"
            ).eq("firebase_uid", firebase_uid).execute()
            
            if not result.data or len(result.data) == 0:
                raise Exception("Kullanıcı bulunamadı")
            
            return result.data[0]
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")
    
    async def update_settings(
        self,
        firebase_uid: str,
        preferred_currency: Optional[str] = None,
        preferred_language: Optional[str] = None,
        notification_enabled: Optional[bool] = None,
        reminder_days: Optional[int] = None,
        theme: Optional[str] = None
    ) -> dict:
        """
        Ayarları güncelle
        """
        try:
            # Güncellenecek alanlar
            update_data = {}
            
            if preferred_currency is not None:
                update_data["preferred_currency"] = preferred_currency
            
            if preferred_language is not None:
                update_data["preferred_language"] = preferred_language
            
            if notification_enabled is not None:
                update_data["notification_enabled"] = notification_enabled
            
            if reminder_days is not None:
                update_data["reminder_days"] = reminder_days
            
            if theme is not None:
                update_data["theme"] = theme
            
            if not update_data:
                # Hiçbir şey güncellenmedi
                return await self.get_settings(firebase_uid)
            
            # UPDATE yap
            self.supabase.table("users").update(
                update_data
            ).eq("firebase_uid", firebase_uid).execute()
            
            # Güncel settings'i döndür
            return await self.get_settings(firebase_uid)
            
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")    

    async def update_fcm_token(self, firebase_uid: str, fcm_token: str) -> dict:
        """
        Kullanıcının cihaz FCM token'ını güncelle
        
        Args:
            firebase_uid: Firebase UID
            fcm_token: FCM token (TEXT)
        
        Returns:
            dict: {fcm_token, updated_at}
        """
        try:
            from datetime import datetime
            updated_at = datetime.utcnow().isoformat()
            
            self.supabase.table("users").update({
                "fcm_token": fcm_token,
                "last_login_at": updated_at  # opsiyonel: etkinlik güncellemesi
            }).eq("firebase_uid", firebase_uid).execute()
            
            return {
                "fcm_token": fcm_token,
                "updated_at": updated_at
            }
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")

    async def get_fcm_token_by_user_id(self, user_id: str) -> Optional[str]:
        """
        Get the user's FCM token by user UUID
        """
        try:
            result = self.supabase.table("users").select("fcm_token").eq(
                "id", user_id
            ).execute()
            if result.data and len(result.data) > 0:
                return result.data[0].get("fcm_token")
            return None
        except Exception as e:
            raise Exception(f"Supabase error: {str(e)}")

# Singleton instance
user_service = UserService()



     
