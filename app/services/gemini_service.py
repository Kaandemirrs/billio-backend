import os
import google.generativeai as genai
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("Gemini API configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure Gemini API: {str(e)}")
        else:
            logger.warning("GEMINI_API_KEY environment variable not found")
    
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
            
            # Gemini'ye istek gönder
            response = await self._generate_content_async(full_prompt)
            
            if response and response.text:
                logger.info(f"Gemini response generated successfully for prompt: '{prompt[:50]}...'")
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
            # Gemini API şu anda doğrudan async desteklemiyor
            # Bu yüzden sync versiyonu kullanıyoruz
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