#!/usr/bin/env python3
"""
Тест исправления karma_service для обработки mixed-type interests.
"""

from app.services.karma_service import KarmaService
import json

# Тест исправления с interests
print('🧪 Тестируем исправление karma_service...')

# Создаем мок-пользователя с разными типами interests
class MockUser:
    persona_name = 'Test User'
    persona_interests_json = '["ai", "technology", 123, null]'  # Смешанные типы
    persona_style_description = 'Test style'
    user_system_prompt = 'Test prompt'
    preferred_ai_model = None

user = MockUser()
service = KarmaService(None, None, None, None, None, None)

# Тестируем _construct_prompt с проблемными interests
try:
    prompt = service._construct_prompt({'text': 'test post', 'channel': {'title': 'test'}}, user)
    print('✅ _construct_prompt работает корректно с mixed-type interests')
    print(f'Часть промпта: {prompt[:300]}...')
except Exception as e:
    print(f'❌ Ошибка в _construct_prompt: {e}')

print('🎉 Тест karma_service завершен!') 