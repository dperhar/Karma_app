import os
import logging
from typing import Optional, Dict, Any
import google.generativeai as genai
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables. Using mock mode.")
            self.mock_mode = True
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.chat = self.model.start_chat(history=[])
            self.mock_mode = False
        
    async def generate_comment(
        self,
        post_content: str,
        user_context: Dict[str, Any],
        channel_context: Dict[str, Any]
    ) -> str:
        """
        Генерирует комментарий на основе контекста поста, пользователя и канала.
        
        Args:
            post_content: Содержимое поста
            user_context: Контекст пользователя (интересы, стиль общения и т.д.)
            channel_context: Контекст канала (тема, аудитория и т.д.)
            
        Returns:
            str: Сгенерированный комментарий
        """
        try:
            if self.mock_mode:
                # Mock response for demo purposes
                return f"Интересная мысль! Особенно понравилось про {post_content[:30]}... 🤔"
            
            prompt = f"""
            Сгенерируй комментарий к посту в Telegram канале.
            
            Контекст поста:
            {post_content}
            
            Контекст пользователя:
            {user_context}
            
            Контекст канала:
            {channel_context}
            
            Комментарий должен быть:
            1. Релевантным теме поста
            2. Соответствовать стилю общения пользователя
            3. Быть естественным и не похожим на бота
            4. Не длиннее 2-3 предложений
            """
            
            response = await self.chat.send_message_async(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating comment with Gemini: {e}")
            raise 