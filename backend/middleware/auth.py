"""Authentication middleware for FastAPI applications."""

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
from models.user.schemas import AdminResponse, UserTelegramResponse
from app.repositories.user_repository import UserRepository

# Configure logger
logger = logging.getLogger(__name__)


class TelegramAuthValidator:
    """Validator for Telegram WebApp init data."""

    @staticmethod
    def validate_telegram_data(init_data: str) -> dict:
        """
        Validates init data from Telegram WebApp

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

            # Get hash to verify
            received_hash = parsed_data.pop("hash")[0]
            logger.debug(f"Received hash: {received_hash}")

            # Sort alphabetically
            data_check_string = "\n".join(
                f"{k}={v[0]}" for k, v in sorted(parsed_data.items())
            )

            # Generate secret key from bot token
            secret_key = hmac.new(
                b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), "sha256"
            ).digest()

            # Calculate hash
            calculated_hash = hmac.new(
                secret_key, data_check_string.encode(), "sha256"
            ).hexdigest()
            logger.debug(f"Calculated hash: {calculated_hash}")

            # Check if it's a test mode
            is_test = parsed_data.get("start_param", [None])[0] == "debug"
            if is_test:
                logger.info("Running in test mode, skipping hash validation")

            # Compare hashes
            if calculated_hash != received_hash and not is_test:
                logger.warning(
                    f"Hash validation failed. Received: {received_hash}, Calculated: {calculated_hash}"
                )
                raise ValueError("Invalid hash")

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
        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
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
            return await call_next(request)

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
                    headers={"WWW-Authenticate": "Bearer"},
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
                    logger.warning(
                        f"User not found in database for telegram_id: {request.state.user.id}"
                    )
                    return JSONResponse(
                        content={
                            "detail": "Registration not completed (user not found)"
                        },
                        status_code=status.HTTP_401_UNAUTHORIZED,
                    )
                return await call_next(request)
            except ValueError as e:
                logger.warning(f"Telegram authentication failed for {path}: {e!s}")
                return JSONResponse(
                    content={"detail": str(e)},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

        # If no valid authentication is provided
        logger.warning(
            f"No authentication provided for protected endpoint: {method} {path}"
        )
        logger.debug(f"Headers: {dict(request.headers)}")
        return JSONResponse(
            content={"detail": "Authentication required"},
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )
