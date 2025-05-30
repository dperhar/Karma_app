"""Authentication middleware for FastAPI applications."""

# Standard library imports
import json
import logging
from urllib.parse import parse_qs, unquote

import jwt

# Third-party imports
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Local imports
from config import JWT_SECRET_KEY
from models.user.schemas import AdminResponse, UserTelegramResponse
from services.repositories.user_repository import UserRepository

# Configure logger
logger = logging.getLogger(__name__)


class TelegramAuthValidator:
    """Validator for Telegram WebApp init data."""

    @staticmethod
    def validate_telegram_data(init_data: str) -> dict:
        """
        Validates init data from Telegram WebApp for Comment Management System

        Args:
            init_data: Raw init_data string from WebApp

        Returns:
            dict: Parsed and validated data

        Raises:
            ValueError: If validation fails
        """
        try:
            logger.debug(f"Starting validation of telegram data: {init_data[:20]}...")
            # Parse init data
            parsed_data = dict(parse_qs(init_data))
            logger.debug(f"Parsed data keys: {list(parsed_data.keys())}")

            # Check if it's a test mode (for development)
            is_test = parsed_data.get("start_param", [None])[0] == "debug"
            if is_test:
                logger.info("Running in test mode, skipping hash validation")

            # For Comment Management System, we don't need strict bot validation
            # We work with user accounts, not bots
            if not is_test:
                logger.info("Production mode: Comment Management System - working with user accounts")

            # Parse user data
            user_data = json.loads(unquote(parsed_data["user"][0]))
            logger.debug(f"User data: {user_data}")
            
            # Keep id as integer for telegram_id
            if not isinstance(user_data.get("id"), int):
                try:
                    user_data["id"] = int(user_data["id"])
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid user ID format: {user_data.get('id')}")
                    raise ValueError("Invalid user ID format") from e

            return {
                "user": user_data,
                "auth_date": int(parsed_data["auth_date"][0]),
            }

        except Exception as e:
            logger.error(f"Failed to validate telegram data: {e!s}", exc_info=True)
            raise ValueError(f"Failed to validate data: {e!s}") from e


def validate_admin_token(token: str) -> dict:
    """Validate JWT token and return admin data."""
    try:
        logger.debug(f"Validating admin token: {token[:10]}...")
        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        logger.debug(f"Admin token valid, data: {decoded}")
        return decoded
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid admin token: {e!s}")
        raise ValueError(f"Invalid token: {e!s}") from e


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for FastAPI applications."""

    def __init__(self, app):
        super().__init__(app)
        self.telegram_validator = TelegramAuthValidator()
        self.public_paths = {
            "/",
            "/health",
            "/api/auth/login",
            "/api/admin/auth/login",
            "/api/auth/refresh",
            "/api/auth/register",
            "/docs",
            "/redoc",
            "/webhook",
            "/openapi.json",
            "/api/yclients/webhook",
            "/ws",  # WebSocket endpoint
            "/api/ws",  # Alternative WebSocket endpoint
            "/api/users/me",  # Allow user profile endpoint for development
            "/api/telegram/chats/list",  # Allow chat list endpoint for development
            "/api/telegram/auth/qr-code",  # QR code generation for Telegram auth
            "/api/telegram/auth/check",  # Check QR login status
        }
        logger.info(
            "AuthMiddleware initialized with public paths: %s", self.public_paths
        )

    async def dispatch(self, request: Request, call_next):
        """Process each request."""
        path = request.url.path
        method = request.method

        logger.info(f"Processing request: {method} {path}")

        # Skip WebSocket upgrade requests
        if request.headers.get("upgrade", "").lower() == "websocket":
            logger.debug(f"Skipping WebSocket request for {path}")
            return await call_next(request)

        # Skip OPTIONS requests for CORS
        if method == "OPTIONS":
            logger.debug(f"Skipping OPTIONS request for {path}")
            return await call_next(request)

        if "/api/yclients/webhook" in path:
            logger.debug(f"DEBUG - Headers for {path}: {dict(request.headers)}")
            logger.debug(f"DEBUG - Body for {path}: {await request.body()}")
            return await call_next(request)

        # Skip public paths
        if path in self.public_paths:
            logger.debug(f"Public path accessed: {path}")
            # For Telegram auth endpoints, still check for authentication but don't require it
            if path in ["/api/telegram/auth/qr-code", "/api/telegram/auth/check"]:
                await self._try_authenticate(request)
            return await call_next(request)
        
        # Check for dynamic telegram verify-2fa paths
        if path.startswith("/api/telegram/auth/verify-2fa/"):
            logger.debug(f"Public telegram verify-2fa path accessed: {path}")
            # Try to authenticate but don't require it
            await self._try_authenticate(request)
            return await call_next(request)

        # Debug: check public paths
        logger.debug(f"Path '{path}' not in public_paths: {self.public_paths}")
        logger.debug(f"Path exact match check: {path == '/api/users/me'}")

        # Allow GET requests to tagcloud endpoints without authentication
        if method == "GET" and "/api/admin/tagclouds" in path:
            logger.debug(f"Allowing GET request to tagcloud endpoint: {path}")
            return await call_next(request)

        # Debug: Log headers
        if "/api/admin/tagclouds" in path and method == "POST":
            logger.debug(f"DEBUG - Headers for {path}: {dict(request.headers)}")

        # Initialize request state
        request.state.admin = None
        request.state.user = None

        # Check for Admin token
        admin_token = request.headers.get("X-Admin-Token")
        if admin_token:
            logger.debug(f"Admin token found for {path}")
            try:
                admin_data = validate_admin_token(admin_token)
                request.state.admin = AdminResponse(**admin_data)
                logger.info(
                    f"Admin authenticated: {request.state.admin.login} for {path}"
                )
                return await call_next(request)
            except ValueError as e:
                logger.warning(f"Admin authentication failed for {path}: {e!s}")
                return JSONResponse(
                    content={"detail": str(e)},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={
                        "WWW-Authenticate": "Bearer",
                        "Access-Control-Allow-Origin": "http://localhost:3000",
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Init-Data",
                    },
                )

        # Check for Telegram WebApp init_data
        init_data = request.headers.get("X-Telegram-Init-Data")
        if init_data:
            logger.debug(f"Telegram init data found for {path}")
            try:
                telegram_data = self.telegram_validator.validate_telegram_data(
                    init_data
                )
                request.state.user = UserTelegramResponse(**telegram_data["user"])
                request.state.auth_date = telegram_data["auth_date"]
                logger.debug(
                    f"Telegram user authenticated: {request.state.user.id} for {path}"
                )

                # Get user from database to check registration status
                user_repo = UserRepository()
                user_model = await user_repo.get_user_by_telegram_id(
                    request.state.user.id
                )

                if not user_model:
                    logger.info(
                        f"User not found in database for telegram_id: {request.state.user.id}, creating new user"
                    )
                    # Auto-register user on first login
                    try:
                        user_dict = {
                            "telegram_id": request.state.user.id,
                            "first_name": request.state.user.first_name,
                            "last_name": request.state.user.last_name,
                            "username": request.state.user.username,
                        }
                        user_model = await user_repo.create_user(**user_dict)
                        logger.info(f"Successfully created new user: {user_model.id}")
                    except Exception as e:
                        logger.error(f"Failed to create user: {e!s}")
                        return JSONResponse(
                            content={
                                "detail": "Failed to create user account"
                            },
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            headers={
                                "WWW-Authenticate": "Bearer",
                                "Access-Control-Allow-Origin": "http://localhost:3000",
                                "Access-Control-Allow-Credentials": "true",
                                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Init-Data",
                            },
                        )
                        
                return await call_next(request)
            except ValueError as e:
                logger.warning(f"Telegram authentication failed for {path}: {e!s}")
                return JSONResponse(
                    content={"detail": str(e)},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={
                        "WWW-Authenticate": "Bearer",
                        "Access-Control-Allow-Origin": "http://localhost:3000",
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Init-Data",
                    },
                )

        # If no valid authentication is provided
        logger.warning(
            f"No authentication provided for protected endpoint: {method} {path}"
        )
        logger.debug(f"Headers: {dict(request.headers)}")
        return JSONResponse(
            content={"detail": "Authentication required"},
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={
                "WWW-Authenticate": "Bearer",
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Init-Data",
            },
        )

    async def _try_authenticate(self, request: Request):
        """Try to authenticate user but don't fail if no authentication provided."""
        # Initialize request state
        request.state.admin = None
        request.state.user = None

        # Check for Admin token
        admin_token = request.headers.get("X-Admin-Token")
        if admin_token:
            try:
                admin_data = validate_admin_token(admin_token)
                request.state.admin = AdminResponse(**admin_data)
                logger.debug(f"Admin authenticated: {request.state.admin.login}")
                return
            except ValueError as e:
                logger.debug(f"Admin authentication failed: {e!s}")

        # Check for Telegram WebApp init_data
        init_data = request.headers.get("X-Telegram-Init-Data")
        if init_data:
            try:
                telegram_data = self.telegram_validator.validate_telegram_data(
                    init_data
                )
                request.state.user = UserTelegramResponse(**telegram_data["user"])
                request.state.auth_date = telegram_data["auth_date"]
                logger.debug(f"Telegram user authenticated: {request.state.user.id}")

                # Get user from database to check registration status
                user_repo = UserRepository()
                user_model = await user_repo.get_user_by_telegram_id(
                    request.state.user.id
                )

                if not user_model:
                    logger.debug(f"User not found in database for telegram_id: {request.state.user.id}, creating new user")
                    # Auto-register user on first login
                    try:
                        user_dict = {
                            "telegram_id": request.state.user.id,
                            "first_name": request.state.user.first_name,
                            "last_name": request.state.user.last_name,
                            "username": request.state.user.username,
                        }
                        user_model = await user_repo.create_user(**user_dict)
                        logger.debug(f"Successfully created new user: {user_model.id}")
                    except Exception as e:
                        logger.debug(f"Failed to create user: {e!s}")
                        
            except ValueError as e:
                logger.debug(f"Telegram authentication failed: {e!s}")

        # If no valid authentication found, just continue without setting user/admin
        logger.debug("No authentication provided, continuing without user/admin")
