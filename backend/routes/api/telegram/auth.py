"""Routes for Telegram authentication."""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from models.base.schemas import APIResponse
from routes.dependencies import get_optional_user
from services.dependencies import container
from services.domain.telegram_messenger.auth_service import TelegramMessengerAuthService
from services.domain.user_service import UserService

router = APIRouter(prefix="/telegram/auth", tags=["telegram-auth"])


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
    current_user: Optional[UserService] = Depends(get_optional_user),
    auth_service: TelegramMessengerAuthService = Depends(
        lambda: container.resolve(TelegramMessengerAuthService)
    ),
) -> APIResponse[LoginCheckResponse]:
    """Check QR code login status."""
    try:
        # Pass current_user.id if user is available, otherwise None
        user_id = current_user.id if current_user else None
        result = await auth_service.check_qr_login(request.token, user_id)
        return APIResponse(success=True, data=LoginCheckResponse(**result))
    except ValueError as e:
        return APIResponse(success=False, message=str(e), status_code=400)
    except Exception as e:
        return APIResponse(success=False, message=str(e))


@router.post("/verify-2fa/{token}", response_model=APIResponse[LoginCheckResponse])
async def verify_qr_2fa(
    token: str,
    request: TwoFactorAuthRequest,
    current_user: Optional[UserService] = Depends(get_optional_user),
    auth_service: TelegramMessengerAuthService = Depends(
        lambda: container.resolve(TelegramMessengerAuthService)
    ),
) -> APIResponse[LoginCheckResponse]:
    """Verify 2FA password for QR code login."""
    try:
        # Pass current_user.id if user is available, otherwise None
        user_id = current_user.id if current_user else None
        result = await auth_service.verify_qr_2fa(
            request.password, token, user_id
        )
        return APIResponse(success=True, data=LoginCheckResponse(**result))
    except ValueError as e:
        return APIResponse(success=False, message=str(e), status_code=400)
    except Exception as e:
        return APIResponse(success=False, message=str(e))
