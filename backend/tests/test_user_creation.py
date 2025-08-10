#!/usr/bin/env python3
"""Test user creation in repository."""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repositories.user_repository import UserRepository


async def test_user_creation():
    """Test user creation."""
    
    user_repo = UserRepository()
    
    try:
        print("🔄 Testing user creation...")
        
        # Check if user exists
        existing_user = await user_repo.get_user_by_telegram_id(118672216)
        if existing_user:
            print(f"✅ User already exists: {existing_user.id}")
            return
        
        # Create new user
        user_dict = {
            "telegram_id": 118672216,
            "first_name": "Pavel", 
            "last_name": "Telitchenko",
            "username": "pivlikk",
        }
        user_model = await user_repo.create_user(**user_dict)
        print(f"✅ User created successfully: {user_model.id}")
            
    except Exception as e:
        print(f"❌ User creation error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_user_creation()) 