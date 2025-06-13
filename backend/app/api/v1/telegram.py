"""API routes for Telegram operations."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.dependencies import get_current_user  
from app.schemas.base import APIResponse
from app.schemas.user import UserResponse
from app.core.dependencies import container

router = APIRouter()


@router.get("/chats/list")
async def get_chats(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """
    Get user's Telegram chats list.
    
    For read operations like this, we return immediate data following 
    the proven pattern from the reference project.
    """
    try:
        # Get TelegramService from container 
        telegram_service = container.telegram_service()
        
        # Get user's Telegram chats directly (following working project pattern)
        chats_data = await telegram_service.get_user_chats(
            user_id=str(current_user.id),
            limit=limit,
            offset=offset
        )
        
        if not chats_data:
            # Check if user has valid Telegram session
            client = await telegram_service.get_or_create_client(str(current_user.id))
            if not client:
                return APIResponse(
                    success=False,
                    data={
                        "chats": [],
                        "total": 0,
                        "limit": limit,
                        "offset": offset,
                        "needs_auth": True,
                    },
                    message="No valid Telegram session found. Please authenticate with Telegram first."
                )
            
            # Check if client is authorized
            is_authorized = await client.is_user_authorized()
            if not is_authorized:
                return APIResponse(
                    success=False,
                    data={
                        "chats": [],
                        "total": 0,
                        "limit": limit,
                        "offset": offset,
                        "needs_auth": True,
                    },
                    message="Telegram session is not authorized. Please complete authentication."
                )
        
        return APIResponse(
            success=True,
            data={
                "chats": chats_data,
                "total": len(chats_data),
                "limit": limit,
                "offset": offset,
            },
            message=f"Successfully retrieved {len(chats_data)} chats from Telegram"
        )
        
    except Exception as e:
        # Graceful error handling - don't expose internal errors to frontend
        return APIResponse(
            success=False,
            data={
                "chats": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            },
            message="Failed to fetch chats from Telegram. Please check your connection and try again."
        ) 