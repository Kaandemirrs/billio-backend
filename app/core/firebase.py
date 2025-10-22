import firebase_admin
from firebase_admin import credentials, auth
import os
from dotenv import load_dotenv

load_dotenv()

# Firebase Admin SDK Initialize
def initialize_firebase():
    """Firebase Admin SDK'yı başlat"""
    try:
        # Zaten initialize edilmişse tekrar etme
        firebase_admin.get_app()
        print("✅ Firebase zaten başlatılmış")
    except ValueError:
        # Service account key path
        cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        
        if not cred_path or not os.path.exists(cred_path):
            raise FileNotFoundError(
                f"Firebase service account key bulunamadı: {cred_path}"
            )
        
        # Credentials
        cred = credentials.Certificate(cred_path)
        
        # Initialize
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin SDK başlatıldı")

# Token verification
async def verify_firebase_token(token: str) -> dict:
    """
    Firebase JWT token'ı doğrula
    
    Args:
        token: Firebase ID token
        
    Returns:
        Decoded token (uid, email, etc.)
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return {
            "success": True,
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False)
        }
    except auth.InvalidIdTokenError:
        return {
            "success": False,
            "error": "INVALID_TOKEN",
            "message": "Token geçersiz"
        }
    except auth.ExpiredIdTokenError:
        return {
            "success": False,
            "error": "TOKEN_EXPIRED",
            "message": "Token süresi dolmuş"
        }
    except Exception as e:
        return {
            "success": False,
            "error": "FIREBASE_ERROR",
            "message": str(e)
        }