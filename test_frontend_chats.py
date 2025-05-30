#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API получения чатов и симуляции фронтенда
"""

import asyncio
import json
import requests
from urllib.parse import quote

# Тестовые данные пользователя
test_user_data = {
    "id": 118672216,
    "first_name": "🔥A1🔥",
    "last_name": "",
    "username": "a1turbotop",
    "language_code": "ru",
    "allows_write_to_pm": True
}

# Кодируем данные пользователя для init_data
user_json = json.dumps(test_user_data, separators=(',', ':'))
init_data_raw = f"user={quote(user_json)}&chat_instance=-1000000000000000000&chat_type=sender&auth_date=1735583847&hash=abcd1234"

def test_chats_api():
    """Тест API получения чатов"""
    url = "http://localhost:8000/api/telegram/chats/list"
    headers = {
        "X-Telegram-Init-Data": init_data_raw,
        "Content-Type": "application/json"
    }
    params = {"limit": 20}
    
    print("🔧 Тестирую API получения чатов...")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"\n📊 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Успешный ответ:")
            print(f"  Success: {data.get('success')}")
            print(f"  Количество чатов: {len(data.get('data', {}).get('chats', []))}")
            
            chats = data.get('data', {}).get('chats', [])
            if chats:
                print(f"\n📝 Первые 5 чатов:")
                for i, chat in enumerate(chats[:5]):
                    print(f"  {i+1}. {chat.get('title')} (ID: {chat.get('telegram_id')}, Type: {chat.get('type')})")
            else:
                print("❌ Чаты не найдены")
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Исключение: {e}")

def test_user_api():
    """Тест API получения пользователя"""
    url = "http://localhost:8000/api/users/me"
    headers = {
        "X-Telegram-Init-Data": init_data_raw,
        "Content-Type": "application/json"
    }
    
    print("\n🔧 Тестирую API получения пользователя...")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"📊 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Успешный ответ:")
            print(f"  Success: {data.get('success')}")
            user_data = data.get('data', {})
            if user_data:
                print(f"  User ID: {user_data.get('id')}")
                print(f"  Telegram ID: {user_data.get('telegram_id')}")
                print(f"  Username: {user_data.get('username')}")
                print(f"  Has valid TG session: {user_data.get('telegram_session_string') is not None}")
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Исключение: {e}")

if __name__ == "__main__":
    print("🚀 Запуск тестов API...")
    print(f"📋 Используемые init_data: {init_data_raw[:100]}...")
    
    test_user_api()
    test_chats_api()
    
    print("\n✨ Тесты завершены!") 