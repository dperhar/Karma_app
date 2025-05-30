#!/usr/bin/env python3
import asyncio
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, '/app')

from services.dependencies import container
from services.domain.user_service import UserService

async def check_user():
    try:
        user_service = container.resolve(UserService)
        user = await user_service.get_user_by_telegram_id(118672216)
        if user:
            print(f'User ID: {user.id}')
            print(f'Has valid TG session: {user.has_valid_tg_session}')
            print(f'Last telegram auth: {user.last_telegram_auth_at}')
        else:
            print('User not found')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    asyncio.run(check_user()) 