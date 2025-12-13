import os
import json
from typing import Optional
import logging
from google.cloud import aiplatform
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2.service_account import Credentials
from app.config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.model = None
        try:
            sa_json_str = settings.VERTEX_AI_SERVICE_ACCOUNT_JSON
            if not sa_json_str:
                logger.warning("VERTEX_AI_SERVICE_ACCOUNT_JSON not configured in settings")
                return

            sa_info = json.loads(sa_json_str)
            credentials = Credentials.from_service_account_info(sa_info)
            project_id = sa_info.get("project_id")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")

            if not project_id:
                logger.error("Service account JSON missing 'project_id'")
                return

            # Initialize Vertex AI
            aiplatform.init(project=project_id, location=location, credentials=credentials)
            vertexai.init(project=project_id, location=location, credentials=credentials)

            # Use auto-updated stable alias for Gemini via Vertex AI
            self.model = GenerativeModel("gemini-2.0-flash")
            logger.info("Vertex AI (Gemini) configured successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {str(e)}")
    
    async def ask_gemini(self, context: str, prompt: str) -> Optional[str]:
        """
        Gemini API kullanarak RAG (Retrieval-Augmented Generation) prompt'u işler
        
        Args:
            context (str): Arama sonuçlarından gelen bağlam bilgisi
            prompt (str): Kullanıcının sorusu
            
        Returns:
            Optional[str]: Gemini'den gelen yanıt veya None
        """
        if not self.model:
            logger.error("Gemini model not configured")
            return None
        
        if not prompt or not prompt.strip():
            logger.warning("Empty prompt provided")
            return None
        
        try:
            # RAG prompt'u oluştur
            full_prompt = self._build_rag_prompt(context, prompt)

            # Gemini'ye istek gönder (sync call wrapped in async function)
            response = await self._generate_content_async(full_prompt)

            if response and getattr(response, "text", None):
                logger.info(f"Gemini response generated successfully for prompt: '{prompt[:50]}...'")
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return None

        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return None

    async def ask_gemini_raw(self, full_prompt: str) -> Optional[str]:
        """
        Özel formatlı bir prompt’u (bağlam + talimatlar dahil) doğrudan Gemini’ye gönderir.

        Args:
            full_prompt (str): Tam prompt metni

        Returns:
            Optional[str]: Yanıt metni veya None
        """
        if not self.model:
            logger.error("Gemini model not configured")
            return None

        if not full_prompt or not full_prompt.strip():
            logger.warning("Empty prompt provided")
            return None

        try:
            response = await self._generate_content_async(full_prompt)
            if response and getattr(response, "text", None):
                logger.info("Gemini raw response generated successfully")
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return None
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return None
    
    def _build_rag_prompt(self, context: str, user_prompt: str) -> str:
        """
        RAG için prompt oluşturur
        
        Args:
            context (str): Arama sonuçlarından gelen bağlam
            user_prompt (str): Kullanıcının sorusu
            
        Returns:
            str: Tam RAG prompt'u
        """
        if not context or not context.strip():
            # Bağlam yoksa sadece kullanıcı sorusunu kullan
            return f"""
Lütfen aşağıdaki soruyu yanıtlayın:

Soru: {user_prompt}

Yanıtınızı Türkçe olarak ve mümkün olduğunca detaylı bir şekilde verin.
"""
        
        return f"""
Aşağıdaki bağlam bilgilerini kullanarak kullanıcının sorusunu yanıtlayın:

BAĞLAM:
{context}

KULLANICI SORUSU:
{user_prompt}

TALIMATLAR:
1. Sadece verilen bağlam bilgilerini kullanarak yanıt verin
2. Bağlamda olmayan bilgileri uydurmayın
3. Yanıtınızı Türkçe olarak verin
4. Eğer bağlamda yeterli bilgi yoksa, bunu belirtin
5. Mümkün olduğunca detaylı ve yararlı bir yanıt verin

YANIT:
"""
    
    async def _generate_content_async(self, prompt: str):
        """
        Gemini API'ye asenkron istek gönderir
        
        Args:
            prompt (str): Gönderilecek prompt
            
        Returns:
            Response object veya None
        """
        try:
            # Vertex AI client currently provides sync generate_content; call it within async flow
            response = self.model.generate_content(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            return None
    
    def is_configured(self) -> bool:
        """
        Gemini servisinin düzgün yapılandırılıp yapılandırılmadığını kontrol eder
        
        Returns:
            bool: Yapılandırma durumu
        """
        return self.model is not None

# Singleton instance
gemini_service = GeminiService()