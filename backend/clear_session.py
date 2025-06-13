#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, '/app')

async def clear_session():
    from app.core.dependencies import container
    from app.repositories.telegram_connection_repository import TelegramConnectionRepository
    
    user_id = '68717fa198504e5aaa8abd61bd7f9533'
    conn_repo = container.resolve(TelegramConnectionRepository)
    
    # Clear the fake session by updating it to inactive
    connection = await conn_repo.get_by_user_id(user_id)
    if connection:
        await conn_repo.create_or_update(
            user_id=user_id,
            session_string_encrypted=None,
            is_active=False,
            validation_status='INVALID'
        )
        print(f'✅ Cleared fake session for user {user_id}')
        print(f'   - Session is now inactive and will force re-authentication')
    else:
        print(f'❌ No session found for user {user_id}')

if __name__ == "__main__":
    asyncio.run(clear_session()) 