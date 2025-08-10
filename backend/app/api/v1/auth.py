"""API routes for authentication."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.core.config import settings
from app.dependencies import get_current_user, get_optional_user
from app.schemas.base import APIResponse
from app.schemas.refresh_token import (
    AccessTokenResponse, RefreshTokenRequest, TokenPair
)
from app.schemas.user import UserResponse
from app.core.dependencies import container
from app.services.jwt_service import JWTService
from app.services.redis_service import RedisService
from app.services.telegram_auth_service import TelegramMessengerAuthService
from app.services.user_service import UserService

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Telegram Authentication ---
telegram_router = APIRouter(prefix="/telegram", tags=["v1-telegram-auth"])


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


class CheckLoginRequest(BaseModel):
    """Request model for checking login status."""

    token: str


class WsTokenResponse(BaseModel):
    token: str


@telegram_router.post("/qr-code", response_model=APIResponse[QRCodeResponse])
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


@telegram_router.post("/check", response_model=APIResponse[LoginCheckResponse])
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
        user_id = current_user.id if current_user else None
        result = await auth_service.check_qr_login(request.token, user_id)

        if result.get("status") == "success" and result.get("user_id"):
            db_user_id = result.get("db_user_id")
            if db_user_id:
                new_session_id = uuid.uuid4().hex
                redis_service: RedisService = container.resolve(RedisService)
                redis_service.save_session(
                    f"web_session:{new_session_id}",
                    {"user_id": db_user_id},
                    expire=settings.SESSION_EXPIRY_SECONDS,
                )
                response.set_cookie(
                    key=settings.SESSION_COOKIE_NAME,
                    value=new_session_id,
                    max_age=settings.SESSION_EXPIRY_SECONDS,
                    httponly=True,
                    secure=not settings.IS_DEVELOP,
                    samesite="lax",
                    path="/",
                )
                await auth_service.user_service.update_user(
                    db_user_id, {"last_telegram_auth_at": datetime.utcnow()}
                )

        return APIResponse(success=True, data=LoginCheckResponse(**result))
    except ValueError as e:
        return APIResponse(success=False, message=str(e), status_code=400)
    except Exception as e:
        return APIResponse(success=False, message=str(e))


@telegram_router.post("/verify-2fa", response_model=APIResponse[LoginCheckResponse])
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
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")

        logger.info(
            f"2FA verification attempt from IP: {client_ip}, User-Agent: {user_agent[:50]}..."
        )

        if not request.token or not request.password:
            logger.warning(
                f"Invalid 2FA request from {client_ip}: missing token or password"
            )
            raise HTTPException(
                status_code=400, detail="Token and password are required"
            )

        if len(request.password) > 50:  # Reasonable limit for 2FA codes
            logger.warning(f"Suspicious 2FA password length from {client_ip}")
            raise HTTPException(status_code=400, detail="Invalid password format")

        user_id = current_user.id if current_user else None
        result = await auth_service.verify_qr_2fa(
            request.password, request.token, user_id
        )

        # Set session cookie if authentication is successful
        if result.get("status") == "success" and result.get("user_id"):
            db_user_id = result.get("db_user_id")
            if db_user_id:
                new_session_id = uuid.uuid4().hex
                redis_service: RedisService = container.resolve(RedisService)
                redis_service.save_session(
                    f"web_session:{new_session_id}",
                    {"user_id": db_user_id},
                    expire=settings.SESSION_EXPIRY_SECONDS,
                )
                response.set_cookie(
                    key=settings.SESSION_COOKIE_NAME,
                    value=new_session_id,
                    max_age=settings.SESSION_EXPIRY_SECONDS,
                    httponly=True,
                    secure=not settings.IS_DEVELOP,
                    samesite="lax",
                    path="/",
                )
                await auth_service.user_service.update_user(
                    db_user_id, {"last_telegram_auth_at": datetime.utcnow()}
                )
                logger.info(f"Session cookie set for user {db_user_id} from {client_ip}")

        logger.info(f"2FA verification successful for user from {client_ip}")
        return APIResponse(success=True, data=LoginCheckResponse(**result))

    except ValueError as e:
        logger.warning(f"2FA verification failed from {client_ip}: {str(e)}")
        return APIResponse(success=False, message=str(e), status_code=400)
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        if "Error verifying 2FA" in error_message:
            logger.warning(
                f"2FA verification service error from {client_ip}: {error_message}"
            )
            return APIResponse(
                success=False, message="Error verifying 2FA", status_code=400
            )

        logger.error(
            f"Unexpected error in 2FA verification from {client_ip}: {error_message}"
        )
        return APIResponse(
            success=False, message="Internal server error", status_code=500
        )


@router.get("/ws-token", response_model=APIResponse[WsTokenResponse])
async def get_ws_token(current_user: UserResponse = Depends(get_current_user)) -> APIResponse[WsTokenResponse]:
    try:
        # Centrifugo connection token with server-side subscription to user's channel
        # Short-lived token to prevent expiry issues on reconnects
        expire = datetime.utcnow() + timedelta(minutes=10)
        channel = f"user:{current_user.id}"
        payload = {
            "sub": str(current_user.id),
            "exp": expire,
            "subs": {
                channel: {}
            }
        }
        token = pyjwt.encode(payload, settings.CENTRIFUGO_TOKEN_HMAC, algorithm="HS256")
        return APIResponse(success=True, data=WsTokenResponse(token=token))
    except Exception as e:
        logger.error(f"Failed to generate WS token: {e}")
        return APIResponse(success=False, message="Failed to generate WS token", status_code=500)


router.include_router(telegram_router) 