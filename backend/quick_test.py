import asyncio
import sys
import os
sys.path.append('/app')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models.user.user import User
from services.external.telethon_client import TelethonClient
from services.external.telethon_service import TelethonService

async def test_user():
    print('Подключаемся к базе данных...')
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@postgres:5432/karma_app_dev')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == 118672216))
        user = result.scalar_one_or_none()
        
        if not user:
            print('Пользователь не найден')
            return
            
        print(f'Пользователь найден: {user.first_name}, session_length: {len(user.telegram_session_string) if user.telegram_session_string else 0}')
        
        telethon_client = TelethonClient()
        telethon_service = TelethonService()
        
        try:
            client = await telethon_client.get_or_create_client(user.id)
            if not client:
                print('Не удалось создать клиент')
                return
                
            print('Проверяем авторизацию...')
            is_authorized = await client.is_user_authorized()
            print(f'Авторизован: {is_authorized}')
            
            if not is_authorized:
                print('Клиент не авторизован')
                return
                
            print('Получаем чаты...')
            chats, _ = await telethon_service.sync_chats(client=client, user_id=user.id, limit=3)
            print(f'Получено чатов: {len(chats)}')
            
            for i, chat in enumerate(chats):
                print(f'{i+1}. {chat.title} (ID: {chat.telegram_id})')
                
        except Exception as e:
            print(f'Ошибка: {e}')
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_user()) 