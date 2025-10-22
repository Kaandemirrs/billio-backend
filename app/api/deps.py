from fastapi import Header, HTTPException, status
from app.core.firebase import verify_firebase_token
from typing import Optional

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    Authorization header'dan Firebase token'ı al ve doğrula
    
    Header format: Bearer <token>
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "NO_TOKEN",
                    "message": "Authorization header bulunamadı"
                }
            }
        )
    
    # "Bearer <token>" formatından token'ı ayıkla
    parts = authorization.split()
    
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_HEADER",
                    "message": "Authorization header formatı hatalı. Format: Bearer <token>"
                }
            }
        )
    
    token = parts[1]
    
    # Token'ı doğrula
    result = await verify_firebase_token(token)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": result.get("error"),
                    "message": result.get("message")
                }
            }
        )
    
    return result