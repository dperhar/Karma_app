"""Routes for Telegram authentication."""

import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Response, Request, HTTPException
from pydantic import BaseModel
import logging

from app.core.config import get_settings
from app.core.dependencies import container
from app.schemas.base import APIResponse
from app.schemas.user import UserResponse
from app.services.auth_service import TelegramMessengerAuthService
from app.services.user_service import UserService

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
async def generate_qr_code() -> APIResponse[QRCodeResponse]:
    """Generate QR code for Telegram login."""
    try:
        # Use dependency injection container
        auth_service = container.resolve(TelegramMessengerAuthService)
        
        result = await auth_service.generate_qr_code()
        return APIResponse(success=True, data=QRCodeResponse(**result))
    except Exception as e:
        return APIResponse(success=False, message=str(e))


@router.post("/check", response_model=APIResponse[LoginCheckResponse])
async def check_qr_login(
    request: CheckLoginRequest,
    response: Response,
) -> APIResponse[LoginCheckResponse]:
    """Check QR code login status."""
    try:
        # Use dependency injection container
        auth_service = container.resolve(TelegramMessengerAuthService)
        
        # Pass None as user_id for now (simplified)
        user_id = None
        result = await auth_service.check_qr_login(request.token, user_id)

        settings = get_settings()
        if result.get("status") == "success" and result.get("user_id"):
            # User successfully logged in, create a web session
            db_user_id = result.get("db_user_id") # This should be set by auth_service
            if db_user_id:
                new_session_id = uuid.uuid4().hex
                # TODO: Implement session storage
                response.set_cookie(
                    key=settings.SESSION_COOKIE_NAME,
                    value=new_session_id,
                    max_age=settings.SESSION_EXPIRY_SECONDS,
                    httponly=True, secure=not settings.IS_DEVELOP, samesite="lax", path="/"
                )

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

        # Use dependency injection container
        auth_service = container.resolve(TelegramMessengerAuthService)
        
        # Pass None as user_id for now (simplified)
        user_id = None
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
