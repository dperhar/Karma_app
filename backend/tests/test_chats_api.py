#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API /telegram/chats/list
"""

import asyncio
import sys
import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Добавляем путь к backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.services.telethon_client import TelethonClient
from app.services.telethon_service import TelethonService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_user_chats():
    """Тестируем получение чатов для пользователя 118672216"""
    
    # Database connection
    engine = create_async_engine(
        "postgresql+asyncpg://karmauser:karmapass@localhost:5432/karmadb"
    )
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Находим пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == 118672216)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error("Пользователь 118672216 не найден в базе данных")
            return
            
        logger.info(f"Найден пользователь: {user.first_name} {user.last_name}")
        logger.info(f"Telegram session string exists: {bool(user.telegram_session_string)}")
        
        if not user.telegram_session_string:
            logger.error("У пользователя нет telegram_session_string")
            return
            
        # Тестируем TelethonClient
        telethon_client = TelethonClient()
        telethon_service = TelethonService()
        
        try:
            client = await telethon_client.get_or_create_client(user.id)
            if not client:
                logger.error("Не удалось создать Telethon клиент")
                return
                
            logger.info("Telethon клиент создан успешно")
            
            # Проверяем авторизацию
            is_authorized = await client.is_user_authorized()
            logger.info(f"Клиент авторизован: {is_authorized}")
            
            if not is_authorized:
                logger.error("Telethon клиент не авторизован")
                return
                
            # Тестируем получение чатов
            logger.info("Начинаем тест получения чатов...")
            chats, pagination = await telethon_service.sync_chats(
                client=client,
                user_id=user.id,
                limit=5
            )
            
            logger.info(f"Получено чатов: {len(chats)}")
            for i, chat in enumerate(chats):
                logger.info(f"  {i+1}. {chat.title} (ID: {chat.telegram_id}, Type: {chat.type})")
                
        except Exception as e:
            logger.error(f"Ошибка при тестировании: {e}", exc_info=True)
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_user_chats()) 