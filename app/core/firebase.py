import firebase_admin
from firebase_admin import credentials, auth
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Firebase Admin SDK Initialize
def initialize_firebase():
    """Firebase Admin SDK'yı başlat"""
    try:
        # Zaten initialize edilmişse tekrar etme
        firebase_admin.get_app()
        print("✅ Firebase zaten başlatılmış")
        return
    except ValueError:
        # Devam edip initialize etmeye çalış
        pass

    # 1) JSON içerikten initialize (Render env: FIREBASE_CREDENTIALS_JSON)
    json_str = os.getenv("FIREBASE_CREDENTIALS_JSON") or os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if json_str:
        try:
            service_account_info = json.loads(json_str)
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK başlatıldı (JSON env)")
            return
        except json.JSONDecodeError as e:
            print(f"⚠️ FIREBASE_CREDENTIALS_JSON parse error: {e}")
        except Exception as e:
            print(f"⚠️ Firebase init error with JSON credentials: {e}")

    # 2) Dosya yolundan initialize (FIREBASE_SERVICE_ACCOUNT_PATH veya GOOGLE_APPLICATION_CREDENTIALS)
    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK başlatıldı (file path)")
            return
        except Exception as e:
            print(f"⚠️ Firebase init error with credential file: {e}")
            raise

    # 3) Hiçbiri yoksa anlamlı hata ver
    raise FileNotFoundError(
        "Firebase credentials not provided. Set FIREBASE_CREDENTIALS_JSON or FIREBASE_SERVICE_ACCOUNT_PATH/GOOGLE_APPLICATION_CREDENTIALS."
    )

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