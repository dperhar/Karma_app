#!/usr/bin/env python3
"""
Быстрый тест для проверки новой системы анализа пользователей после применения diff.
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.user_context_analysis_service import UserContextAnalysisService

class MockUserRepository:
    async def get_user(self, user_id):
        class MockUser:
            id = user_id
            telegram_id = 123456789
            persona_interests_json = None
            persona_style_description = None
            user_system_prompt = None
        return MockUser()
    
    async def update_user(self, user_id, **kwargs):
        print(f"📝 Обновление пользователя {user_id}: {kwargs}")
        return True

class MockTelethonService:
    async def sync_chats(self, client, user_id, limit=50):
        class MockChat:
            id = "test_chat"
            telegram_id = "123"
            title = "Test Chat"
            is_channel = False
            is_group = True
            is_user = False
        return [MockChat()]
    
    async def sync_chat_messages(self, client, chat_id, limit=100):
        return [
            {"sender_telegram_id": 123456789, "text": "Привет! Как дела?", "date": "2023-01-01"},
            {"sender_telegram_id": 123456789, "text": "Очень интересно про AI и технологии 🤖", "date": "2023-01-02"},
            {"sender_telegram_id": 987654321, "text": "Не наше сообщение", "date": "2023-01-03"},
        ]

class MockGeminiService:
    async def generate_content(self, prompt):
        if "interests" in prompt.lower():
            return {"content": "artificial intelligence, technology, programming, innovation, machine learning"}
        else:
            return {"content": "Casual and friendly communication style with moderate emoji usage and tech-focused interests."}

async def test_new_analysis_system():
    """Тестируем новую систему анализа пользователей."""
    print("🚀 Тестирование новой системы анализа пользователей...")
    
    # Создаем сервис с мок-объектами
    service = UserContextAnalysisService(
        user_repository=MockUserRepository(),
        telethon_service=MockTelethonService(),
        gemini_service=MockGeminiService()
    )
    
    # Тестируем новые методы
    print("\n1️⃣ Тестируем _fetch_content_for_topic_analysis...")
    content_data = await service._fetch_content_for_topic_analysis(None, "test_user")
    print(f"   Получено текстов для анализа тем: {len(content_data.get('texts', []))}")
    
    print("\n2️⃣ Тестируем _fetch_user_sent_messages_for_style...")
    user_messages = await service._fetch_user_sent_messages_for_style(None, "test_user")
    print(f"   Получено собственных сообщений пользователя: {len(user_messages)}")
    
    print("\n3️⃣ Тестируем _analyze_communication_style с новыми V-категориями...")
    style_analysis = await service._analyze_communication_style(user_messages)
    print(f"   Категории анализа: {list(style_analysis.keys())}")
    print(f"   Новые V-категории найдены: {'lexical_parameters' in style_analysis}")
    
    print("\n4️⃣ Тестируем _extract_interests_and_topics...")
    interests_analysis = await service._extract_interests_and_topics(["AI and machine learning", "technology trends", "programming"])
    print(f"   Найдено интересов: {len(interests_analysis.get('interests', []))}")
    print(f"   Интересы: {interests_analysis.get('interests', [])[:5]}")
    
    print("\n5️⃣ Полный анализ пользователя...")
    try:
        result = await service.analyze_user_context(None, "test_user")
        print(f"   Статус анализа: {result.get('status')}")
        if result.get('status') == 'completed':
            print("   ✅ Анализ завершен успешно!")
        else:
            print(f"   ⚠️ Анализ завершен с проблемой: {result.get('reason')}")
    except Exception as e:
        print(f"   ❌ Ошибка анализа: {e}")
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(test_new_analysis_system()) 