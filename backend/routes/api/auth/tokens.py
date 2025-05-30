"""API routes for token management."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from models.base.schemas import APIResponse
from models.user.refresh_token_schemas import (
    AccessTokenResponse,
    RefreshTokenRequest,
    TokenPair,
)
from routes.dependencies import get_current_user
from services.dependencies import container
from services.domain.jwt_service import JWTService
from services.domain.user_service import UserService

router = APIRouter(prefix="/api/auth", tags=["authentication"])

logger = logging.getLogger(__name__)


def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Extract client information from request."""
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    return user_agent, ip_address


@router.post("/token", response_model=APIResponse[TokenPair])
async def create_token_pair(
    request: Request,
    current_user: UserService = Depends(get_current_user),
    jwt_service: JWTService = Depends(lambda: container.resolve(JWTService)),
) -> APIResponse[TokenPair]:
    """Create access and refresh token pair for authenticated user."""
    try:
        user_agent, ip_address = get_client_info(request)
        
        token_pair = await jwt_service.create_token_pair(
            user_id=current_user.id,
            device_info=user_agent,
            ip_address=ip_address,
        )
        
        return APIResponse(
            success=True,
            data=token_pair,
            message="Token pair created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating token pair: {e}")
        return APIResponse(
            success=False,
            message=f"Failed to create token pair: {str(e)}"
        )


@router.post("/refresh", response_model=APIResponse[AccessTokenResponse])
async def refresh_access_token(
    request_data: RefreshTokenRequest,
    jwt_service: JWTService = Depends(lambda: container.resolve(JWTService)),
) -> APIResponse[AccessTokenResponse]:
    """Refresh access token using refresh token."""
    try:
        new_access_token = await jwt_service.refresh_access_token(
            request_data.refresh_token
        )
        
        return APIResponse(
            success=True,
            data=new_access_token,
            message="Access token refreshed successfully"
        )
        
    except HTTPException as e:
        return APIResponse(
            success=False,
            message=e.detail,
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return APIResponse(
            success=False,
            message="Failed to refresh token"
        )


@router.post("/revoke", response_model=APIResponse[dict])
async def revoke_refresh_token(
    request_data: RefreshTokenRequest,
    jwt_service: JWTService = Depends(lambda: container.resolve(JWTService)),
) -> APIResponse[dict]:
    """Revoke a refresh token."""
    try:
        success = await jwt_service.revoke_refresh_token(request_data.refresh_token)
        
        if success:
            return APIResponse(
                success=True,
                data={"revoked": True},
                message="Refresh token revoked successfully"
            )
        else:
            return APIResponse(
                success=False,
                message="Refresh token not found"
            )
            
    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        return APIResponse(
            success=False,
            message="Failed to revoke token"
        )


@router.post("/revoke-all", response_model=APIResponse[dict])
async def revoke_all_user_tokens(
    current_user: UserService = Depends(get_current_user),
    jwt_service: JWTService = Depends(lambda: container.resolve(JWTService)),
) -> APIResponse[dict]:
    """Revoke all refresh tokens for current user."""
    try:
        revoked_count = await jwt_service.revoke_all_user_tokens(current_user.id)
        
        return APIResponse(
            success=True,
            data={"revoked_count": revoked_count},
            message=f"Revoked {revoked_count} refresh tokens"
        )
        
    except Exception as e:
        logger.error(f"Error revoking all tokens: {e}")
        return APIResponse(
            success=False,
            message="Failed to revoke tokens"
        )


@router.get("/token-info", response_model=APIResponse[dict])
async def get_token_info(
    current_user: UserService = Depends(get_current_user),
    jwt_service: JWTService = Depends(lambda: container.resolve(JWTService)),
) -> APIResponse[dict]:
    """Get information about user's active tokens."""
    try:
        token_count = await jwt_service.get_user_token_count(current_user.id)
        
        return APIResponse(
            success=True,
            data={
                "user_id": current_user.id,
                "active_refresh_tokens": token_count,
                "access_token_expires_in_minutes": 15,  # ACCESS_TOKEN_EXPIRE_MINUTES
            },
            message="Token information retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting token info: {e}")
        return APIResponse(
            success=False,
            message="Failed to get token information"
        ) 