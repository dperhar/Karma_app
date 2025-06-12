"""Authentication middleware for validating requests."""

# Standard library imports
import hmac
import json
import logging
from urllib.parse import parse_qs, unquote

import jwt

# Third-party imports
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Local imports
from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.schemas.user import AdminResponse, UserTelegramResponse
from app.core.dependencies import container
from app.services.redis_service import RedisService
from app.services.user_service import UserService

# Configure logger
logger = logging.getLogger(__name__)


class TelegramAuthValidator:
    """Telegram WebApp data validator."""

    @staticmethod
    def validate_telegram_data(init_data: str, bot_token: str) -> dict:
        """Validate Telegram WebApp init data."""
        try:
            # Parse the init data
            params = dict(parse_qs(init_data, keep_blank_values=True))
            
            # Extract hash and remove it from params for validation
            received_hash = params.pop('hash', [None])[0]
            if not received_hash:
                raise ValueError("Missing hash")
            
            # Create data string for validation
            data_check_arr = []
            for key, value_list in sorted(params.items()):
                if value_list and value_list[0]:  # Check if value exists and is not empty
                    value = unquote(value_list[0])
                    data_check_arr.append(f"{key}={value}")
            
            if not data_check_arr:
                raise ValueError("Missing required fields")
            
            data_check_string = '\n'.join(data_check_arr)
            
            # Create secret key
            secret_key = hmac.new(
                "WebAppData".encode(), 
                bot_token.encode(), 
                digestmod='sha256'
            ).digest()
            
            # Calculate hash
            calculated_hash = hmac.new(
                secret_key, 
                data_check_string.encode(), 
                digestmod='sha256'
            ).hexdigest()
            
            # Verify hash
            if not hmac.compare_digest(calculated_hash, received_hash):
                raise ValueError("Invalid hash")
            
            # Parse user data if available
            user_data = None
            if 'user' in params and params['user'][0]:
                try:
                    user_data = json.loads(unquote(params['user'][0]))
                except json.JSONDecodeError:
                    raise ValueError("Invalid user data format")
            
            return {
                'valid': True,
                'user': user_data,
                'params': params
            }
            
        except Exception as e:
            logger.error(f"Failed to validate telegram data: {e}")
            raise ValueError(f"Failed to validate data: {e}")


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authentication middleware."""

    # Paths that don't require authentication
    SKIP_AUTH_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/telegram/auth/qr-code",
        "/api/v1/telegram/auth/check",
        "/api/v1/telegram/auth/verify-2fa",
    }
    
    # Paths that require admin authentication  
    ADMIN_ONLY_PATHS = {
        "/api/v1/admin"
    }

    async def dispatch(self, request: Request, call_next):
        """Process request through authentication."""
        path = request.url.path
        method = request.method
        
        # Always allow OPTIONS requests (for CORS preflight)
        if method == "OPTIONS":
            return await call_next(request)
        
        # Skip authentication for certain paths
        if path in self.SKIP_AUTH_PATHS or path.startswith("/static/"):
            return await call_next(request)
        
        # Log request processing
        logger.info(f"Processing request: {method} {path}")
        
        try:
            # Check for admin authentication first
            if any(path.startswith(admin_path) for admin_path in self.ADMIN_ONLY_PATHS):
                admin_user = await self._check_admin_auth(request)
                if admin_user:
                    request.state.admin_user = admin_user
                    return await call_next(request)
                else:
                    return self._auth_error("Admin authentication required")
            
            # Check for session authentication
            session_user = await self._check_session_auth(request)
            if session_user:
                request.state.user = session_user
                return await call_next(request)
            
            # Check for Telegram authentication
            telegram_user = await self._check_telegram_auth(request)
            if telegram_user:
                request.state.user = telegram_user
                return await call_next(request)
            
            # No valid authentication found
            logger.warning(f"No authentication provided for protected endpoint: {method} {path}")
            return self._auth_error("Authentication required")
            
        except Exception as e:
            logger.error(f"Authentication error for {method} {path}: {e}")
            return self._auth_error("Authentication failed")

    async def _check_admin_auth(self, request: Request) -> dict:
        """Check admin JWT token authentication."""
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                admin_id = payload.get("admin_id")
                
                if admin_id:
                    logger.info(f"Admin authentication successful for admin_id: {admin_id}")
                    return {"admin_id": admin_id, "role": "admin"}
                
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid admin token: {e}")
                
        except Exception as e:
            logger.error(f"Admin auth check failed: {e}")
        
        return None

    async def _check_session_auth(self, request: Request) -> dict:
        """Check session cookie authentication."""
        try:
            # Get session cookie
            session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
            if not session_cookie:
                return None
            
            logger.info(f"Found session cookie: {session_cookie[:10]}...")
            
            # Get Redis service
            redis_service = container.resolve(RedisService)
            
            # Get session data from Redis
            session_key = f"web_session:{session_cookie}"
            session_data = redis_service.get_session(session_key)
            
            if not session_data:
                logger.warning(f"Session not found in Redis: {session_key}")
                return None
            
            logger.info(f"Session data found: {session_data}")
            
            # Validate session data
            user_id = session_data.get("user_id")
            if not user_id:
                logger.warning("No user_id in session data")
                return None
            
            # Get user service and fetch user data
            user_service = container.resolve(UserService)
            user = await user_service.get_user_by_telegram_id(user_id)
            
            if not user:
                logger.warning(f"User not found for telegram_id: {user_id}")
                return None
            
            logger.info(f"Session authentication successful for user_id: {user_id}")
            return {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "auth_method": "session"
            }
            
        except Exception as e:
            logger.error(f"Session auth check failed: {e}")
        
        return None

    async def _check_telegram_auth(self, request: Request) -> dict:
        """Check Telegram init data authentication."""
        try:
            init_data = request.headers.get("X-Telegram-Init-Data")
            if not init_data:
                return None
            
            logger.info(f"Found Telegram init data: {init_data[:50]}...")
            
            # Skip validation for mock data used with Telethon
            if init_data == "mock_init_data_for_telethon":
                logger.info("Using mock Telegram init data for Telethon - skipping validation")
                # For Telethon, we need to get user from session or other means
                # This is a fallback - ideally session auth should handle this
                return None
            
            # Validate Telegram data
            result = TelegramAuthValidator.validate_telegram_data(init_data, settings.TELEGRAM_BOT_TOKEN)
            
            if result['valid'] and result['user']:
                user_data = result['user']
                telegram_id = user_data.get('id')
                
                if telegram_id:
                    # Get user service and fetch user data  
                    user_service = container.resolve(UserService)
                    user = await user_service.get_user_by_telegram_id(telegram_id)
                    
                    if user:
                        logger.info(f"Telegram authentication successful for user_id: {telegram_id}")
                        return {
                            "id": user.id,
                            "telegram_id": user.telegram_id,
                            "username": user.username,
                            "auth_method": "telegram"
                        }
                    else:
                        logger.warning(f"User not found for telegram_id: {telegram_id}")
            
        except Exception as e:
            logger.warning(f"Telegram authentication failed for {request.url.path}: {e}")
        
        return None

    def _auth_error(self, message: str) -> JSONResponse:
        """Return authentication error response."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": message},
            headers={"WWW-Authenticate": "Bearer"},
        )
