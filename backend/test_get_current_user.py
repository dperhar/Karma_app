#!/usr/bin/env python3
"""Test get_current_user function."""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routes.dependencies import get_current_user
from services.domain.user_service import UserService
from services.dependencies import container


class MockRequest:
    """Mock request object for testing."""
    
    def __init__(self, telegram_user=None):
        self.method = "GET"
        self.state = MockState(telegram_user)


class MockState:
    """Mock state object."""
    
    def __init__(self, telegram_user=None):
        self.user = telegram_user
        self.admin = None
        self.auth_date = None


class MockTelegramUser:
    """Mock Telegram user."""
    
    def __init__(self, user_id=118672216):
        self.id = user_id
        self.first_name = "Pavel"
        self.last_name = "Telitchenko"
        self.username = "pivlikk"


async def test_get_current_user():
    """Test get_current_user function."""
    
    try:
        print("🔄 Testing get_current_user...")
        
        # Create mock request with telegram user
        telegram_user = MockTelegramUser()
        request = MockRequest(telegram_user)
        
        # Get user service from container
        user_service = container.resolve(UserService)
        
        # Call get_current_user
        result = await get_current_user(request, user_service)
        
        print(f"✅ get_current_user successful: {result}")
            
    except Exception as e:
        print(f"❌ get_current_user error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_get_current_user()) 