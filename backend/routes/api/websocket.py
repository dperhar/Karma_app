"""
API routes for WebSocket authentication with Centrifugo.
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException

from models.base.schemas import APIResponse
from models.user.schemas import UserResponse
from routes.dependencies import get_current_user
from services.jwt_service import generate_ws_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/websocket", tags=["websocket"])


@router.get("/token", response_model=APIResponse[dict])
async def get_websocket_token(current_user: UserResponse = Depends(get_current_user)):
    """
    Generate a WebSocket token for the current authenticated user.

    This token should be used to connect to the Centrifugo WebSocket endpoint.
    Returns connection information including token, WebSocket URL, and available channels.
    """
    try:
        # Generate a token that expires in 24 hours
        token = generate_ws_token(current_user.id)

        # Get WebSocket URL from environment or use default
        ws_url = os.getenv(
            "CENTRIFUGO_WS_URL", "ws://localhost:9000/connection/websocket"
        )

        # Prepare connection data
        connection_data = {
            "token": token,
            "ws_url": ws_url,  # Centrifugo WebSocket URL
            "user": current_user.id,
            "channels": [
                f"user:{current_user.id}",  # User's personal channel
            ],
        }

        # Return standardized API response
        return APIResponse(
            success=True,
            data=connection_data,
            message="WebSocket token generated successfully",
        )
    except Exception as e:
        logger.error(f"Error generating WebSocket token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
