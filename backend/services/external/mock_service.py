import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

class MockService:
    def __init__(self):
        self.mock_channels = [
            {"id": 1, "name": "Tech News", "type": "channel"},
            {"id": 2, "name": "Startup Hub", "type": "channel"},
            {"id": 3, "name": "AI Research", "type": "channel"},
        ]
        
        self.mock_posts = [
            {
                "id": 1,
                "channel_id": 1,
                "content": "Новый iPhone 15 Pro Max получил революционную камеру и процессор A17 Pro",
                "date": datetime.now() - timedelta(hours=2),
                "reactions": {"👍": 150, "❤️": 75, "🔥": 45}
            },
            {
                "id": 2,
                "channel_id": 2,
                "content": "Стартап из России привлек $10M инвестиций для разработки квантового компьютера",
                "date": datetime.now() - timedelta(hours=5),
                "reactions": {"👍": 200, "❤️": 100, "🔥": 80}
            },
            {
                "id": 3,
                "channel_id": 3,
                "content": "OpenAI представил GPT-5 с улучшенными возможностями мультимодального обучения",
                "date": datetime.now() - timedelta(hours=1),
                "reactions": {"👍": 300, "❤️": 150, "🔥": 120}
            }
        ]
        
        self.mock_user_context = {
            "interests": ["AI", "Technology", "Startups"],
            "writing_style": "Профессиональный, с элементами юмора",
            "reaction_history": {
                "👍": 45,
                "❤️": 30,
                "🔥": 25
            }
        }
    
    async def get_channels(self) -> List[Dict[str, Any]]:
        """Возвращает список мок-каналов"""
        return self.mock_channels
    
    async def get_posts(self, channel_id: int = None) -> List[Dict[str, Any]]:
        """Возвращает список мок-постов"""
        if channel_id:
            return [post for post in self.mock_posts if post["channel_id"] == channel_id]
        return self.mock_posts
    
    async def get_user_context(self) -> Dict[str, Any]:
        """Возвращает мок-контекст пользователя"""
        return self.mock_user_context
    
    async def generate_mock_comment(self, post_id: int) -> str:
        """Генерирует мок-комментарий для поста"""
        post = next((p for p in self.mock_posts if p["id"] == post_id), None)
        if not post:
            raise ValueError(f"Post with id {post_id} not found")
            
        mock_comments = [
            "Отличная новость! Особенно интересно про квантовые вычисления.",
            "Очень перспективное направление. Слежу за развитием проекта.",
            "Интересно, как это повлияет на рынок в целом?",
            "Отличная статья! Спасибо за подробный разбор.",
            "Очень впечатляющие результаты. Жду продолжения!"
        ]
        
        return random.choice(mock_comments) 