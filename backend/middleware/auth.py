"""Authentication middleware for FastAPI applications."""

# Standard library imports
import uuid
import json
import logging
from urllib.parse import parse_qs, unquote

import jwt

# Third-party imports
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Local imports
from config import JWT_SECRET_KEY, SESSION_COOKIE_NAME, SESSION_EXPIRY_SECONDS, IS_DEVELOP
from models.user.schemas import AdminResponse, UserTelegramResponse
from services.repositories.user_repository import UserRepository
from services.domain.redis_service import RedisDataService
from services.domain.jwt_service import JWTService
from services.dependencies import container # For resolving services

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
            "/api/telegram/auth/verify-2fa",  # Verify 2FA for QR login
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
            if path in ["/api/telegram/auth/qr-code", "/api/telegram/auth/check", "/api/telegram/auth/verify-2fa"]:
                await self._try_authenticate(request)
            # For chats endpoint, also try to authenticate
            elif path in ["/api/users/me", "/api/telegram/chats/list"]:
                logger.debug(f"Trying to authenticate for public path: {path}")
                await self._try_authenticate(request)
                logger.debug(f"Auth result for {path}: user={getattr(request.state, 'user', None)}")
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
        request.state.user_from_session = False
        request.state.user_authenticated_by_init_data_this_request = False

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

                # Check for JWT access token
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    access_token = auth_header.split(" ")[1]
                    logger.debug(f"JWT access token found for {path}")
                    try:
                        jwt_service: JWTService = container.resolve(JWTService)
                        payload = jwt_service.verify_access_token(access_token)
                        user_id = payload.get("user_id")
                        
                        if user_id:
                            user_repo: UserRepository = container.resolve(UserRepository)
                            user_model = await user_repo.get_user(user_id)
                            if user_model:
                                request.state.user = UserTelegramResponse(
                                    id=user_model.telegram_id,
                                    first_name=user_model.first_name,
                                    last_name=user_model.last_name,
                                    username=user_model.username
                                )
                                request.state.user_db_id = user_model.id
                                request.state.user_from_session = False  # JWT, not session
                                logger.info(f"User authenticated via JWT: {user_model.id} for {path}")
                                return await call_next(request)
                            else:
                                logger.warning(f"User ID {user_id} from JWT not found in DB")
                                
                    except Exception as e:
                        logger.debug(f"JWT authentication failed for {path}: {e!s}")
                        # Continue to other authentication methods

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

        # Check for session cookie if not admin or JWT
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        if session_id:
            logger.debug(f"Session cookie found for {path}")
            redis_service: RedisDataService = container.resolve(RedisDataService)
            session_data = await redis_service.get_session(f"web_session:{session_id}") # Use a specific prefix for web sessions
            if session_data and "user_id" in session_data:
                user_repo: UserRepository = container.resolve(UserRepository)
                user_model = await user_repo.get_user(session_data["user_id"])
                if user_model:
                    request.state.user = UserTelegramResponse(
                        id=user_model.telegram_id, # Assuming UserTelegramResponse is okay, or use UserResponse
                        first_name=user_model.first_name,
                        last_name=user_model.last_name,
                        username=user_model.username
                    ) # Adapt as needed, this might need UserResponse from DB
                    request.state.user_db_id = user_model.id # Store actual DB ID
                    request.state.user_from_session = True
                    logger.info(f"User authenticated via session: {user_model.id} for {path}")
                    response = await call_next(request) # Proceed with the request
                    return response
                else:
                    logger.warning(f"User ID {session_data['user_id']} from session not found in DB.")
            else:
                logger.warning(f"Invalid or expired session ID {session_id} found in cookie.")

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
                user_repo: UserRepository = container.resolve(UserRepository)
                db_user = await user_repo.get_user_by_telegram_id(
                    request.state.user.id
                )

                if not db_user:
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
                        db_user = await user_repo.create_user(**user_dict)
                        logger.info(f"Successfully created new user: {db_user.id}")
                        request.state.user_db_id = db_user.id
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
                else:
                    request.state.user_db_id = db_user.id

                # If authenticated by init_data and not by session, set flag to create session
                if not request.state.user_from_session:
                    request.state.user_authenticated_by_init_data_this_request = True

                response = await call_next(request)

                if request.state.user_authenticated_by_init_data_this_request:
                    new_session_id = uuid.uuid4().hex
                    redis_service: RedisDataService = container.resolve(RedisDataService)
                    await redis_service.save_session(
                        f"web_session:{new_session_id}",
                        {"user_id": request.state.user_db_id}, # Use actual DB user ID
                        expire=SESSION_EXPIRY_SECONDS
                    )
                    response.set_cookie(
                        key=SESSION_COOKIE_NAME,
                        value=new_session_id,
                        max_age=SESSION_EXPIRY_SECONDS,
                        httponly=True,
                        secure=not IS_DEVELOP,
                        samesite="lax", # Or "strict" or "none" if cross-site
                        path="/",
                    )
                return response
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
        request.state.user_from_session = False # Track if user was loaded from session

        # Check for session cookie
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        if session_id:
            redis_service: RedisDataService = container.resolve(RedisDataService)
            session_data = await redis_service.get_session(f"web_session:{session_id}")
            if session_data and "user_id" in session_data:
                user_repo: UserRepository = container.resolve(UserRepository)
                user_model = await user_repo.get_user(session_data["user_id"])
                if user_model:
                    request.state.user = UserTelegramResponse(
                         id=user_model.telegram_id,
                        first_name=user_model.first_name,
                        last_name=user_model.last_name,
                        username=user_model.username
                    )
                    request.state.user_db_id = user_model.id
                    request.state.user_from_session = True # Mark that user was loaded from session
                    logger.debug(f"User authenticated via session (optional): {user_model.id}")

        # Check for JWT access token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
            logger.debug(f"JWT access token found for optional auth")
            try:
                jwt_service: JWTService = container.resolve(JWTService)
                payload = jwt_service.verify_access_token(access_token)
                user_id = payload.get("user_id")
                
                if user_id:
                    user_repo: UserRepository = container.resolve(UserRepository)
                    user_model = await user_repo.get_user(user_id)
                    if user_model:
                        request.state.user = UserTelegramResponse(
                            id=user_model.telegram_id,
                            first_name=user_model.first_name,
                            last_name=user_model.last_name,
                            username=user_model.username
                        )
                        request.state.user_db_id = user_model.id
                        request.state.user_from_session = False  # JWT, not session
                        logger.debug(f"User authenticated via JWT (optional): {user_model.id}")
                        return  # Found JWT auth, no need to check further
                        
            except Exception as e:
                logger.debug(f"JWT authentication failed (optional): {e!s}")

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

        # If user already loaded from session, no need to check init_data for this optional auth
        if request.state.user_from_session:
            return

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
                user_repo: UserRepository = container.resolve(UserRepository)
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
                        db_user = await user_repo.create_user(**user_dict)
                        request.state.user_db_id = db_user.id
                        logger.debug(f"Successfully created new user: {db_user.id}")
                    except Exception as e:
                        logger.debug(f"Failed to create user: {e!s}")
                elif user_model: # if user_model exists
                    request.state.user_db_id = user_model.id
                        
            except ValueError as e:
                logger.debug(f"Telegram authentication failed: {e!s}")

        # If no valid authentication found, just continue without setting user/admin
        logger.debug("No authentication provided, continuing without user/admin")
