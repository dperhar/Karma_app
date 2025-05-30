#!/usr/bin/env python3
"""Test authentication middleware."""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from middleware.auth import TelegramAuthValidator


async def test_auth():
    """Test Telegram auth validation."""
    
    test_data = "user=%7B%22id%22%3A118672216%2C%22first_name%22%3A%22Pavel%22%2C%22last_name%22%3A%22Telitchenko%22%2C%22username%22%3A%22pivlikk%22%2C%22language_code%22%3A%22en%22%2C%22is_premium%22%3Atrue%2C%22allows_write_to_pm%22%3Atrue%7D&auth_date=1716922846&signature=SignaturePkdisAdGwQepp8pmdCeUM6k_NKjxU5aiofGrn_SomeRandomSigna-UzResG0mLxuPcQZT5rlnWDw&hash=89d6079ad6762351f38c6dbbc41bb53048019256a9443988af7a48bcad16ba31&start_param=debug&chat_type=sender&chat_instance=8428209589180549439"
    
    validator = TelegramAuthValidator()
    
    try:
        result = validator.validate_telegram_data(test_data)
        print(f"✅ Validation successful: {result}")
        
        # Test user creation
        from services.repositories.user_repository import UserRepository
        
        user_repo = UserRepository()
        
        # Check if user exists
        user_model = await user_repo.get_user_by_telegram_id(118672216)
        
        if user_model:
            print(f"✅ User already exists: {user_model.id}")
        else:
            print("⚠️ User doesn't exist, creating...")
            user_dict = {
                "telegram_id": 118672216,
                "first_name": "Pavel", 
                "last_name": "Telitchenko",
                "username": "pivlikk",
            }
            user_model = await user_repo.create_user(**user_dict)
            print(f"✅ User created: {user_model.id}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_auth()) 