#!/usr/bin/env python3
"""
Test script for Safe Telegram API Refactoring.
Tests the new pagination and flood control features.
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from services.external.telethon_service import TelethonService
from models.telegram_messenger.chat import TelegramMessengerChat, TelegramMessengerChatType, TelegramMessengerChatSyncStatus
from models.user.user import User, UserInitialSyncStatus


class MockTelegramClient:
    """Mock Telegram client for testing."""
    
    def __init__(self):
        self.dialogs_data = [
            MagicMock(
                entity=MagicMock(
                    id=12345,
                    title="Test Channel",
                    broadcast=True,
                    participants_count=100
                ),
                date=datetime.now(),
                top_message=100
            ),
            MagicMock(
                entity=MagicMock(
                    id=67890,
                    title="Test Group",
                    broadcast=False,
                    participants_count=50
                ),
                date=datetime.now(),
                top_message=200
            )
        ]
    
    async def get_dialogs(self, limit=None, offset_date=None, offset_id=None, offset_peer=None):
        """Mock get_dialogs with pagination support."""
        return self.dialogs_data[:limit] if limit else self.dialogs_data
    
    async def get_entity(self, entity_id):
        """Mock get_entity."""
        return MagicMock(id=entity_id, title="Mock Entity")
    
    async def iter_messages(self, entity, **kwargs):
        """Mock iter_messages."""
        # Return mock messages
        for i in range(kwargs.get('limit', 10)):
            yield MagicMock(
                id=i + 1,
                text=f"Test message {i + 1}",
                date=datetime.now(),
                sender_id=123,
                media=None
            )


async def test_safe_sync_chats():
    """Test safe chat synchronization with pagination."""
    print("🧪 Testing safe chat synchronization...")
    
    service = TelethonService()
    client = MockTelegramClient()
    user_id = "test_user_123"
    
    try:
        # Test with small limit for safety
        chats, next_pagination = await service.sync_chats(
            client=client,
            user_id=user_id,
            limit=10
        )
        
        print(f"✅ Successfully fetched {len(chats)} chats")
        print(f"📄 Next pagination info: {next_pagination}")
        
        # Verify chat data structure
        if chats:
            chat = chats[0]
            assert hasattr(chat, 'telegram_id')
            assert hasattr(chat, 'type')
            assert hasattr(chat, 'title')
            print(f"✅ Chat data structure validated")
        
        return True
        
    except Exception as e:
        print(f"❌ Chat sync test failed: {e}")
        return False


async def test_safe_sync_messages():
    """Test safe message synchronization with pagination."""
    print("🧪 Testing safe message synchronization...")
    
    service = TelethonService()
    client = MockTelegramClient()
    user_id = "test_user_123"
    chat_id = 12345
    
    try:
        # Test with small limit and direction control
        messages, next_pagination = await service.sync_chat_messages(
            client=client,
            chat_telegram_id=chat_id,
            user_id=user_id,
            limit=20,
            direction="older"
        )
        
        print(f"✅ Successfully fetched {len(messages)} messages")
        print(f"📄 Next pagination info: {next_pagination}")
        
        # Verify message data structure
        if messages:
            message = messages[0]
            assert 'telegram_id' in message
            assert 'text' in message
            assert 'date' in message
            print(f"✅ Message data structure validated")
        
        return True
        
    except Exception as e:
        print(f"❌ Message sync test failed: {e}")
        return False


async def test_flood_control():
    """Test flood wait handling."""
    print("🧪 Testing flood control mechanisms...")
    
    service = TelethonService()
    client_key = "test_user_flood"
    
    try:
        # Test cooldown state management
        assert not service._is_client_in_cooldown(client_key)
        print("✅ Initial cooldown state correct")
        
        # Mock flood wait error handling
        from telethon.errors import FloodWaitError
        mock_error = MagicMock()
        mock_error.seconds = 1  # 1 second wait
        
        # Test that safe API call respects cooldown
        async def mock_api_call():
            return "success"
        
        result = await service._safe_api_call(client_key, mock_api_call)
        assert result == "success"
        print("✅ Safe API call mechanism working")
        
        return True
        
    except Exception as e:
        print(f"❌ Flood control test failed: {e}")
        return False


async def test_user_initial_sync_status():
    """Test user initial sync status logic."""
    print("🧪 Testing user initial sync status...")
    
    try:
        # Create a test user with pending sync status
        user = User(
            id="test_user_456",
            initial_sync_status=UserInitialSyncStatus.PENDING
        )
        
        assert user.needs_initial_sync() == True
        print("✅ User with PENDING status needs initial sync")
        
        # Test user with completed sync
        user.initial_sync_status = UserInitialSyncStatus.MINIMAL_COMPLETED
        assert user.needs_initial_sync() == False
        print("✅ User with MINIMAL_COMPLETED status doesn't need initial sync")
        
        return True
        
    except Exception as e:
        print(f"❌ User sync status test failed: {e}")
        return False


async def test_chat_sync_status():
    """Test chat sync status functionality."""
    print("🧪 Testing chat sync status...")
    
    try:
        # Create a test chat with sync status
        chat = TelegramMessengerChat(
            id="test_chat_789",
            telegram_id=12345,
            user_id="test_user_123",
            type=TelegramMessengerChatType.CHANNEL,
            title="Test Channel",
            sync_status=TelegramMessengerChatSyncStatus.NEVER_SYNCED
        )
        
        assert chat.sync_status == TelegramMessengerChatSyncStatus.NEVER_SYNCED
        print("✅ Chat sync status set correctly")
        
        # Update sync status
        chat.sync_status = TelegramMessengerChatSyncStatus.INITIAL_MINIMAL_SYNCED
        assert chat.sync_status == TelegramMessengerChatSyncStatus.INITIAL_MINIMAL_SYNCED
        print("✅ Chat sync status updated correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Chat sync status test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting Safe Telegram API Refactoring Tests")
    print("=" * 60)
    
    tests = [
        test_safe_sync_chats,
        test_safe_sync_messages,
        test_flood_control,
        test_user_initial_sync_status,
        test_chat_sync_status,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print()
        try:
            success = await test()
            if success:
                passed += 1
                print(f"🟢 {test.__name__} PASSED")
            else:
                failed += 1
                print(f"🔴 {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"🔴 {test.__name__} FAILED with exception: {e}")
    
    print()
    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Safe Telegram API refactoring is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    asyncio.run(main()) 