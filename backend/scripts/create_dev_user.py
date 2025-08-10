#!/usr/bin/env python3
"""Create development user in database."""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.repositories.user_repository import UserRepository

async def ensure_dev_user(repo: UserRepository, *, user_id: str, telegram_id: int, first_name: str, last_name: str | None, username: str | None):
    existing = await repo.get_user_by_telegram_id(telegram_id)
    if existing:
        print(f'User already exists: {existing.id} | telegram_id: {existing.telegram_id}')
        return existing

    user_data = {
        'id': user_id,
        'telegram_id': telegram_id,
        'first_name': first_name,
        'last_name': last_name,
        'username': username,
        'telegram_chats_load_limit': 100,
        'telegram_messages_load_limit': 100
    }
    user = await repo.create_user(**user_data)
    print(f'User created: {user.id} | telegram_id: {user.telegram_id}')
    return user


async def create_dev_user():
    """Create development users required for local testing."""
    repo = UserRepository()

    # Original dev user
    await ensure_dev_user(
        repo,
        user_id='dev-user-1',
        telegram_id=118672216,
        first_name='Pavel',
        last_name='Telitchenko',
        username='pivlikk',
    )

    # Frontend dev telegram_id used by middleware fallback
    await ensure_dev_user(
        repo,
        user_id='dev-user-109005276',
        telegram_id=109005276,
        first_name='Development',
        last_name='User',
        username='dev109005276',
    )

if __name__ == '__main__':
    asyncio.run(create_dev_user()) 