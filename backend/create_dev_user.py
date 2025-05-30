#!/usr/bin/env python3
"""Create development user in database."""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.user.user import User
from services.repositories.user_repository import UserRepository

async def create_dev_user():
    """Create or get development user."""
    repo = UserRepository()
    
    # Check if user already exists
    existing = await repo.get_user_by_telegram_id(118672216)
    if existing:
        print(f'User already exists: {existing.id} | telegram_id: {existing.telegram_id}')
        return existing
    
    # Create new user
    user_data = {
        'id': 'dev-user-1',
        'telegram_id': 118672216,
        'first_name': 'Pavel',
        'last_name': 'Telitchenko', 
        'username': 'pivlikk',
        'telegram_chats_load_limit': 100,
        'telegram_messages_load_limit': 100
    }
    
    try:
        user = await repo.create_user(**user_data)
        print(f'User created: {user.id} | telegram_id: {user.telegram_id}')
        return user
    except Exception as e:
        print(f'Error creating user: {e}')
        raise

if __name__ == '__main__':
    asyncio.run(create_dev_user()) 