from app.core.supabase import get_supabase_admin_client
from typing import Dict, List, Optional
from datetime import datetime

class NotificationService:
    """Notification service"""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
    
    async def get_notifications(
        self,
        user_id: str,
        is_read: Optional[bool] = None,
        type: Optional[str] = None,
        limit: int = 20,
        page: int = 1
    ) -> Dict:
        """
        Bildirimleri listele
        
        Args:
            user_id: User UUID
            is_read: Okunma filtresi
            type: Tip filtresi
            limit: Sayfa başına kayıt
            page: Sayfa numarası
            
        Returns:
            Notifications, unread_count, pagination
        """
        try:
            # Query builder
            query = self.supabase.table("notifications").select(
                "*", count="exact"
            ).eq("user_id", user_id).order("created_at", desc=True)
            
            # Filters
            if is_read is not None:
                query = query.eq("is_read", is_read)
            
            if type:
                query = query.eq("type", type)
            
            # Pagination
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)
            
            # Execute
            result = query.execute()
            
            notifications = result.data if result.data else []
            total_items = result.count if result.count else 0
            
            # Unread count
            unread_count = await self.get_unread_count(user_id)
            
            # Pagination
            total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
            
            return {
                "notifications": notifications,
                "unread_count": unread_count,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages,
                    "total_items": total_items
                }
            }
            
        except Exception as e:
            raise Exception(f"Get notifications error: {str(e)}")
    
    async def get_notification_by_id(
        self,
        user_id: str,
        notification_id: str
    ) -> Optional[Dict]:
        """Tek bir bildirimi getir"""
        try:
            result = self.supabase.table("notifications").select("*").eq(
                "id", notification_id
            ).eq("user_id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return None
            
        except Exception as e:
            raise Exception(f"Get notification error: {str(e)}")
    
    async def get_unread_count(self, user_id: str) -> int:
        """Okunmamış bildirim sayısı"""
        try:
            result = self.supabase.table("notifications").select(
                "id", count="exact"
            ).eq("user_id", user_id).eq("is_read", False).execute()
            
            return result.count if result.count else 0
            
        except Exception as e:
            raise Exception(f"Unread count error: {str(e)}")
    
    async def mark_as_read(
        self,
        user_id: str,
        notification_id: str
    ) -> Dict:
        """Bildirimi okundu işaretle"""
        try:
            now = datetime.utcnow().isoformat()
            
            # UPDATE
            self.supabase.table("notifications").update({
                "is_read": True,
                "read_at": now
            }).eq("id", notification_id).eq("user_id", user_id).execute()
            
            return {
                "id": notification_id,
                "is_read": True,
                "read_at": now
            }
            
        except Exception as e:
            raise Exception(f"Mark read error: {str(e)}")
    
    async def mark_all_as_read(self, user_id: str) -> Dict:
        """Tüm bildirimleri okundu işaretle"""
        try:
            now = datetime.utcnow().isoformat()
            
            # Okunmamışları say
            count_result = self.supabase.table("notifications").select(
                "id", count="exact"
            ).eq("user_id", user_id).eq("is_read", False).execute()
            
            marked_count = count_result.count if count_result.count else 0
            
            # UPDATE
            if marked_count > 0:
                self.supabase.table("notifications").update({
                    "is_read": True,
                    "read_at": now
                }).eq("user_id", user_id).eq("is_read", False).execute()
            
            return {
                "marked_count": marked_count,
                "marked_at": now
            }
            
        except Exception as e:
            raise Exception(f"Mark all read error: {str(e)}")
    
    async def delete_notification(
        self,
        user_id: str,
        notification_id: str
    ) -> bool:
        """Bildirimi sil"""
        try:
            self.supabase.table("notifications").delete().eq(
                "id", notification_id
            ).eq("user_id", user_id).execute()
            
            return True
            
        except Exception as e:
            raise Exception(f"Delete error: {str(e)}")
    
    async def clear_all_notifications(
        self,
        user_id: str,
        type: Optional[str] = None
    ) -> Dict:
        """Tüm bildirimleri temizle"""
        try:
            # Say
            query = self.supabase.table("notifications").select(
                "id", count="exact"
            ).eq("user_id", user_id)
            
            if type:
                query = query.eq("type", type)
            
            count_result = query.execute()
            deleted_count = count_result.count if count_result.count else 0
            
            # DELETE
            if deleted_count > 0:
                delete_query = self.supabase.table("notifications").delete().eq(
                    "user_id", user_id
                )
                
                if type:
                    delete_query = delete_query.eq("type", type)
                
                delete_query.execute()
            
            return {
                "deleted_count": deleted_count,
                "deleted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Clear all error: {str(e)}")
    
    async def create_test_notification(
        self,
        user_id: str,
        type: str,
        title: str,
        message: str,
        action_type: Optional[str] = None,
        action_data: Optional[Dict] = None
    ) -> Dict:
        """Test bildirimi oluştur"""
        try:
            import json
            
            notification_data = {
                "user_id": user_id,
                "type": type,
                "title": title,
                "message": message,
                "action_type": action_type,
                "action_data": json.dumps(action_data) if action_data else None,
                "sent_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("notifications").insert(
                notification_data
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            raise Exception("Bildirim oluşturulamadı")
            
        except Exception as e:
            raise Exception(f"Create test notification error: {str(e)}")

# Singleton instance
notification_service = NotificationService()