from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.max_requests = 60  # Dakikada 60 istek
        self.window = 60  # 60 saniye
    
    async def check_rate_limit(self, request: Request):
        """Rate limit kontrolü"""
        # IP veya user_id al
        client_ip = request.client.host
        
        # Mevcut zamanı al
        now = datetime.utcnow()
        
        # Eski istekleri temizle (60 saniyeden eski)
        cutoff = now - timedelta(seconds=self.window)
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > cutoff
        ]
        
        # İstek sayısını kontrol et
        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Dakikada maksimum {self.max_requests} istek yapabilirsiniz. Lütfen bekleyin."
                    }
                }
            )
        
        # İsteği kaydet
        self.requests[client_ip].append(now)

# Singleton instance
rate_limiter = RateLimiter()