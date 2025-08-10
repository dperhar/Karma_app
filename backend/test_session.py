#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, '/app')

from app.core.dependencies import container
from app.services.user_service import UserService
from app.repositories.telegram_connection_repository import TelegramConnectionRepository
from app.core.security import get_encryption_service

async def test_session_creation():
    user_service = container.resolve(UserService)
    conn_repo = TelegramConnectionRepository()
    encryption_service = get_encryption_service()
    
    # Test user ID from the API response
    user_id = '68717fa198504e5aaa8abd61bd7f9533'
    
    print(f"Testing session creation for user {user_id}")
    
    # Create a test session
    test_session = 'test_session_string_for_user_109005276'
    encrypted_session = encryption_service.encrypt_session_string(test_session)
    
    print(f"Encrypted session: {encrypted_session[:20]}...")
    
    # Save to telegram_connections table
    connection = await conn_repo.create_or_update(
        user_id=user_id,
        session_string_encrypted=encrypted_session,
        is_active=True,
        validation_status='VALID'
    )
    
    print(f'Created connection for user {user_id}')
    
    # Test the user has_valid_tg_session now
    user = await user_service.get_user(user_id)
    print(f'User has_valid_tg_session: {user.has_valid_tg_session if user else None}')

if __name__ == "__main__":
    asyncio.run(test_session_creation()) 