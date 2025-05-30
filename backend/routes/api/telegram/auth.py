"""Routes for Telegram authentication."""

import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Response, Request, HTTPException
from pydantic import BaseModel
import logging

from config import SESSION_COOKIE_NAME, SESSION_EXPIRY_SECONDS, IS_DEVELOP
from models.base.schemas import APIResponse
from models.user.schemas import UserResponse
from routes.dependencies import get_optional_user
from services.dependencies import container
from services.domain.telegram_messenger.auth_service import TelegramMessengerAuthService
from services.domain.redis_service import RedisDataService
from services.domain.user_service import UserService

router = APIRouter(prefix="/telegram/auth", tags=["telegram-auth"])
logger = logging.getLogger(__name__)


class QRCodeResponse(BaseModel):
    """Response model for QR code generation."""

    token: str


class LoginCheckResponse(BaseModel):
    """Response model for login check."""

    requires_2fa: Optional[bool] = None
    user_id: Optional[int] = None
    status: Optional[str] = None


class TwoFactorAuthRequest(BaseModel):
    """Request model for 2FA verification."""

    token: str
    password: str


class TwoFactorPasswordRequest(BaseModel):
    """Request model for 2FA verification with token in path."""

    password: str


class CheckLoginRequest(BaseModel):
    """Request model for checking login status."""

    token: str


@router.post("/qr-code", response_model=APIResponse[QRCodeResponse])
async def generate_qr_code(
    auth_service: TelegramMessengerAuthService = Depends(
        lambda: container.resolve(TelegramMessengerAuthService)
    ),
) -> APIResponse[QRCodeResponse]:
    """Generate QR code for Telegram login."""
    try:
        result = await auth_service.generate_qr_code()
        return APIResponse(success=True, data=QRCodeResponse(**result))
    except Exception as e:
        return APIResponse(success=False, message=str(e))


@router.post("/check", response_model=APIResponse[LoginCheckResponse])
async def check_qr_login(
    request: CheckLoginRequest,
    response: Response,
    current_user: Optional[UserResponse] = Depends(get_optional_user),
    auth_service: TelegramMessengerAuthService = Depends(
        lambda: container.resolve(TelegramMessengerAuthService)
    ),
) -> APIResponse[LoginCheckResponse]:
    """Check QR code login status."""
    try:
        # Pass current_user.id if user is available, otherwise None
        user_id = current_user.id if current_user else None
        result = await auth_service.check_qr_login(request.token, user_id)

        if result.get("status") == "success" and result.get("user_id"):
            # User successfully logged in, create a web session
            db_user_id = result.get("db_user_id") # This should be set by auth_service
            if db_user_id:
                new_session_id = uuid.uuid4().hex
                redis_service: RedisDataService = container.resolve(RedisDataService)
                redis_service.save_session(
                    f"web_session:{new_session_id}",
                    {"user_id": db_user_id},
                    expire=SESSION_EXPIRY_SECONDS # Use config value
                )
                response.set_cookie(
                    key=SESSION_COOKIE_NAME, # Use config value
                    value=new_session_id,
                    max_age=SESSION_EXPIRY_SECONDS,
                    httponly=True, secure=not IS_DEVELOP, samesite="lax", path="/"
                )
                await auth_service.user_service.update_user(db_user_id, {"last_telegram_auth_at": datetime.utcnow()})

        return APIResponse(success=True, data=LoginCheckResponse(**result)) # type: ignore
    except ValueError as e:
        return APIResponse(success=False, message=str(e), status_code=400)
    except Exception as e:
        return APIResponse(success=False, message=str(e))


@router.post("/verify-2fa", response_model=APIResponse[LoginCheckResponse])
async def verify_qr_2fa(
    request: TwoFactorAuthRequest,
    response: Response,
    http_request: Request,
    current_user: Optional[UserResponse] = Depends(get_optional_user),
    auth_service: TelegramMessengerAuthService = Depends(
        lambda: container.resolve(TelegramMessengerAuthService)
    ),
) -> APIResponse[LoginCheckResponse]:
    """Verify 2FA password for QR code login."""
    try:
        # Security checks
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")
        
        # Log security-relevant information (without sensitive data)
        logger.info(f"2FA verification attempt from IP: {client_ip}, User-Agent: {user_agent[:50]}...")
        
        # Basic input validation
        if not request.token or not request.password:
            logger.warning(f"Invalid 2FA request from {client_ip}: missing token or password")
            raise HTTPException(status_code=400, detail="Token and password are required")
        
        if len(request.password) > 50:  # Reasonable limit for 2FA codes
            logger.warning(f"Suspicious 2FA password length from {client_ip}")
            raise HTTPException(status_code=400, detail="Invalid password format")

        # Pass current_user.id if user is available, otherwise None
        user_id = current_user.id if current_user else None
        result = await auth_service.verify_qr_2fa(
            request.password, request.token, user_id
        )
        
        logger.info(f"2FA verification successful for user from {client_ip}")
        return APIResponse(success=True, data=LoginCheckResponse(**result))
        
    except ValueError as e:
        logger.warning(f"2FA verification failed from {client_ip}: {str(e)}")
        return APIResponse(success=False, message=str(e), status_code=400)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Check if it's a service-level error that should be handled gracefully
        error_message = str(e)
        if "Error verifying 2FA" in error_message:
            logger.warning(f"2FA verification service error from {client_ip}: {error_message}")
            return APIResponse(success=False, message="Error verifying 2FA", status_code=400)
        
        logger.error(f"Unexpected error in 2FA verification from {client_ip}: {error_message}")
        return APIResponse(success=False, message="Internal server error", status_code=500)
