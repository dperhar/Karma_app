"""API routes for Telegram posts."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from models.user.schemas import UserResponse
from routes.dependencies import get_current_user
from services.dependencies import get_telethon_service, get_telethon_client

logger = logging.getLogger(__name__)

router = APIRouter()


class PostsResponse(BaseModel):
    """Response model for posts list."""
    posts: list[dict]
    total: int
    page: int
    limit: int


@router.get("/posts", response_model=PostsResponse)
async def get_posts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Posts per page"),
    current_user: UserResponse = Depends(get_current_user),
    telethon_service=Depends(get_telethon_service),
    telethon_client=Depends(get_telethon_client),
):
    """Get recent posts from user's Telegram channels/chats.
    
    Args:
        page: Page number (1-based)
        limit: Number of posts per page (1-100)
        current_user: Authenticated user
        telethon_service: Telethon service instance
        telethon_client: Telethon client instance
        
    Returns:
        PostsResponse with posts data
    """
    try:
        # Get Telegram client for the user
        # get_current_user ensures user is authenticated with the app.
        # get_or_create_client will check the Telegram session string from the DB.
        client = await telethon_client.get_or_create_client(current_user.id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Telegram session is not active or invalid. Please log in again via Settings."
            )

        # Calculate offset
        offset = (page - 1) * limit

        # Get posts from Telegram
        posts = await telethon_service.get_user_posts(
            client=client,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )

        return PostsResponse(
            posts=posts,
            total=len(posts),  # This is just the current page count, we'd need to implement proper total counting
            page=page,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Error getting posts for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch posts"
        ) from e


@router.get("/posts/{post_id}")
async def get_post(
    post_id: int,
    channel_id: int = Query(description="Telegram channel ID"),
    current_user: UserResponse = Depends(get_current_user),
    telethon_service=Depends(get_telethon_service),
    telethon_client=Depends(get_telethon_client),
):
    """Get a specific post by ID.
    
    Args:
        post_id: Telegram post/message ID
        channel_id: Telegram channel ID
        current_user: Authenticated user
        telethon_service: Telethon service instance
        telethon_client: Telethon client instance
        
    Returns:
        Post data dictionary
    """
    try:
        # Get Telegram client for the user
        client = await telethon_client.get_or_create_client(current_user.id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Telegram session is not active or invalid. Please log in again via Settings."
            )

        # Get the specific message
        try:
            entity = await client.get_entity(channel_id)
            message = await client.get_messages(entity, ids=[post_id])
            
            if not message or not message[0]:
                raise HTTPException(
                    status_code=404,
                    detail="Post not found"
                )
                
            # Convert message to post data
            post_data = await telethon_service._create_post_from_message(message[0], entity)
            
            if not post_data:
                raise HTTPException(
                    status_code=404,
                    detail="Failed to process post"
                )
                
            return post_data
            
        except Exception as e:
            logger.error(f"Error getting post {post_id} from channel {channel_id}: {e}")
            raise HTTPException(
                status_code=404,
                detail="Post not found or access denied"
            ) from e

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting post {post_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch post"
        ) from e 