#!/usr/bin/env python3
"""Test /users/me endpoint directly."""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.users import get_user
from app.dependencies import get_current_user
from app.services.user_service import UserService
from app.core.dependencies import container


class MockTelegramUser:
    """Mock Telegram user."""
    
    def __init__(self, user_id=118672216):
        self.id = user_id
        self.first_name = "Pavel"
        self.last_name = "Telitchenko"
        self.username = "pivlikk"


async def test_user_endpoint():
    """Test /users/me endpoint."""
    
    try:
        print("🔄 Testing /users/me endpoint...")
        
        # Get user service from container
        user_service = container.resolve(UserService)
        
        # Get user directly from service
        user = await user_service.get_user_by_telegram_id(118672216)
        
        if not user:
            print("❌ User not found in database")
            return
            
        print(f"✅ User found: {user.id}")
        
        # Call the endpoint function directly
        result = await get_user(current_user=user)
        
        print(f"✅ Endpoint successful: {result}")
            
    except Exception as e:
        print(f"❌ Endpoint error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_user_endpoint()) 