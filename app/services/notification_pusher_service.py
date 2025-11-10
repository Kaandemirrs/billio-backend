from firebase_admin import messaging


async def send_push_notification(fcm_token: str, title: str, message: str) -> dict:
    """Send an FCM push notification to a device token"""
    try:
        notification = messaging.Notification(title=title, body=message)
        msg = messaging.Message(token=fcm_token, notification=notification)
        message_id = messaging.send(msg)
        return {"sent": True, "message_id": message_id}
    except Exception as e:
        # Swallow error to avoid failing API flow; return diagnostic
        return {"sent": False, "error": str(e)}