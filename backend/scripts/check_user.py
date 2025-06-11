#!/usr/bin/env python3
import asyncio
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.dependencies import container
from app.services.user_service import UserService

async def check_user():
    try:
        user_service = container.resolve(UserService)
        user = await user_service.get_user_by_telegram_id(5912181683)  # Replace with your Telegram ID
        
        if user:
            print(f"✅ User found: {user.telegram_id} - {user.first_name}")
        else:
            print("❌ User not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_user()) 