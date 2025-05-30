#!/usr/bin/env python3
"""Debug middleware issues."""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from middleware.auth import AuthMiddleware


class MockRequest:
    """Mock request object for testing."""
    
    def __init__(self, headers=None, path="/api/users/me"):
        self.headers = headers or {}
        self.url = MockURL(path)
        self.state = MockState()
        self.method = "GET"
    
    def get(self, key, default=None):
        return self.headers.get(key, default)


class MockURL:
    """Mock URL object."""
    
    def __init__(self, path):
        self.path = path


class MockState:
    """Mock state object."""
    
    def __init__(self):
        self.user = None
        self.admin = None
        self.auth_date = None


async def test_middleware():
    """Test middleware with mock request."""
    
    test_data = "user=%7B%22id%22%3A118672216%2C%22first_name%22%3A%22Pavel%22%2C%22last_name%22%3A%22Telitchenko%22%2C%22username%22%3A%22pivlikk%22%2C%22language_code%22%3A%22en%22%2C%22is_premium%22%3Atrue%2C%22allows_write_to_pm%22%3Atrue%7D&auth_date=1716922846&signature=SignaturePkdisAdGwQepp8pmdCeUM6k_NKjxU5aiofGrn_SomeRandomSigna-UzResG0mLxuPcQZT5rlnWDw&hash=89d6079ad6762351f38c6dbbc41bb53048019256a9443988af7a48bcad16ba31&start_param=debug&chat_type=sender&chat_instance=8428209589180549439"
    
    request = MockRequest({
        "X-Telegram-Init-Data": test_data,
        "Content-Type": "application/json"
    })
    
    middleware = AuthMiddleware(None)
    
    async def mock_call_next(req):
        return {"status": "success"}
    
    try:
        print("🔄 Testing middleware...")
        result = await middleware.dispatch(request, mock_call_next)
        print(f"✅ Middleware successful: {result}")
            
    except Exception as e:
        print(f"❌ Middleware error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_middleware()) 