"""API routes for Telegram operations."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from pydantic import BaseModel
from datetime import datetime
import uuid
import logging

from app.dependencies import get_current_user, get_optional_user  
from app.schemas.base import APIResponse
from app.schemas.user import UserResponse, UserCreate
from app.core.dependencies import container
from app.services.auth_service import TelegramMessengerAuthService
from app.core.config import settings
from app.services.redis_service import RedisService
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Telegram Authentication Endpoints ---
class QRCodeResponse(BaseModel):
    """Response model for QR code generation."""
    token: str

class LoginCheckResponse(BaseModel):
    """Response model for login check."""
    status: str
    message: Optional[str] = None
    user_id: Optional[str] = None
    db_user_id: Optional[str] = None
    requires_2fa: Optional[bool] = None

class CheckLoginRequest(BaseModel):
    """Request model for checking login status."""
    token: str

class TwoFactorAuthRequest(BaseModel):
    """Request model for 2FA verification."""
    token: str
    password: str

@router.post("/auth/qr-code", response_model=APIResponse[QRCodeResponse])
async def generate_qr_code() -> APIResponse[QRCodeResponse]:
    """Generate QR code for Telegram login."""
    try:
        auth_service = container.resolve(TelegramMessengerAuthService)
        result = await auth_service.generate_qr_code()
        return APIResponse(success=True, data=QRCodeResponse(**result))
    except Exception as e:
        return APIResponse(success=False, message=str(e))

@router.post("/auth/check", response_model=APIResponse[LoginCheckResponse])
async def check_qr_login(
    request: CheckLoginRequest,
    response: Response,
    current_user: Optional[UserResponse] = Depends(get_optional_user),
) -> APIResponse[LoginCheckResponse]:
    """Check QR code login status."""
    try:
        auth_service = container.resolve(TelegramMessengerAuthService)
        user_id = current_user.id if current_user else None
        result = await auth_service.check_qr_login(request.token, user_id)
        
        if result.get("status") == "success" and result.get("user_id"):
            from app.services.user_service import UserService
            user_service = container.resolve(UserService)
            tg_id = int(result.get("user_id"))
            session_str = result.get("session_string")

            # If current_user exists but belongs to a different telegram_id, switch to the correct user
            target_user = None
            try:
                if current_user and current_user.telegram_id and current_user.telegram_id != tg_id:
                    target_user = await user_service.get_user_by_telegram_id(tg_id)
                    if not target_user:
                        target_user = await user_service.create_user(UserCreate(telegram_id=tg_id))
                elif current_user and current_user.telegram_id == tg_id:
                    target_user = current_user
                else:
                    target_user = await user_service.get_user_by_telegram_id(tg_id)
                    if not target_user:
                        target_user = await user_service.create_user(UserCreate(telegram_id=tg_id))
                # Persist session string under target user
                if session_str and target_user:
                    await user_service.update_user_tg_session(target_user.id, session_str)
                # Issue backend session cookie for target user
                if target_user:
                    new_session_id = uuid.uuid4().hex
                    redis_service = container.resolve(RedisService)
                    redis_service.save_session(
                        f"web_session:{new_session_id}",
                        {"user_id": target_user.id},
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
                    result["db_user_id"] = str(target_user.id)
                    # Trigger reset-and-seed for the new active session
                    try:
                        from app.tasks.tasks import reset_and_seed_user_data
                        reset_and_seed_user_data.delay(user_id=str(target_user.id), chats_limit=target_user.telegram_chats_load_limit or 20, per_chat_limit=target_user.telegram_messages_load_limit or 50, source="channels")
                    except Exception:
                        pass
            except Exception as e_bind:
                logger.error(f"Failed to bind/switch user on QR login: {e_bind}", exc_info=True)
        
        # Convert user_id to string if it exists (Telegram returns integer)  
        if result.get("user_id"):
            result["user_id"] = str(result["user_id"])
        if result.get("db_user_id"):
            result["db_user_id"] = str(result["db_user_id"])
            
        return APIResponse(success=True, data=LoginCheckResponse(**result))
    except ValueError as e:
        return APIResponse(success=False, message=str(e), status_code=400)
    except Exception as e:
        return APIResponse(success=False, message=str(e))

@router.post("/auth/verify-2fa", response_model=APIResponse[LoginCheckResponse])
async def verify_qr_2fa(
    request: TwoFactorAuthRequest,
    response: Response,
    http_request: Request,
    current_user: Optional[UserResponse] = Depends(get_optional_user),
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

        auth_service = container.resolve(TelegramMessengerAuthService)
        user_id = current_user.id if current_user else None
        result = await auth_service.verify_qr_2fa(
            request.password, request.token, user_id
        )

        # Set session cookie if authentication is successful
        if result.get("status") == "success" and result.get("user_id"):
            # Bind to the correct user: if current_user has different telegram_id, switch
            try:
                from app.services.user_service import UserService
                user_service = container.resolve(UserService)
                tg_id = int(result.get("user_id"))
                session_str = result.get("session_string")
                target_user = None
                if current_user and current_user.telegram_id and current_user.telegram_id != tg_id:
                    target_user = await user_service.get_user_by_telegram_id(tg_id)
                    if not target_user:
                        target_user = await user_service.create_user(UserCreate(telegram_id=tg_id))
                elif current_user and current_user.telegram_id == tg_id:
                    target_user = current_user
                else:
                    target_user = await user_service.get_user_by_telegram_id(tg_id)
                    if not target_user:
                        target_user = await user_service.create_user(UserCreate(telegram_id=tg_id))
                if session_str and target_user:
                    await user_service.update_user_tg_session(target_user.id, session_str)
                if target_user:
                    new_session_id = uuid.uuid4().hex
                    redis_service = container.resolve(RedisService)
                    redis_service.save_session(
                        f"web_session:{new_session_id}",
                        {"user_id": target_user.id},
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
                    result["db_user_id"] = str(target_user.id)
                # Trigger reset-and-seed after successful 2FA
                try:
                    from app.tasks.tasks import reset_and_seed_user_data
                    reset_and_seed_user_data.delay(user_id=str(target_user.id), chats_limit=target_user.telegram_chats_load_limit or 20, per_chat_limit=target_user.telegram_messages_load_limit or 50, source="channels")
                except Exception:
                    pass
            except Exception as e_bind:
                logger.error(f"Failed to bind/switch user on 2FA: {e_bind}", exc_info=True)

        logger.info(f"2FA verification result for user from {client_ip}: {result.get('status')}")
        
        # Convert user_id to string if it exists (Telegram returns integer)
        if result.get("user_id"):
            result["user_id"] = str(result["user_id"])
        if result.get("db_user_id"):
            result["db_user_id"] = str(result["db_user_id"])
            
        return APIResponse(success=True, data=LoginCheckResponse(**result))

    except ValueError as e:
        logger.warning(f"2FA verification failed from {client_ip}: {str(e)}")
        return APIResponse(success=False, message=str(e), status_code=400)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in 2FA verification from {client_ip}: {str(e)}")
        return APIResponse(success=False, message="Internal server error", status_code=500)

# --- Chat Endpoints ---

@router.post("/chats/sync", response_model=APIResponse[dict])
async def sync_chats(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Trigger syncing of Telegram chats to the database.
    
    This endpoint triggers a background task to fetch chats from Telegram
    and save them to the database for later use in the feed.
    """
    try:
        # Import the task here to avoid circular imports
        from app.tasks.tasks import fetch_telegram_chats_task
        
        # Trigger the background task
        task_result = fetch_telegram_chats_task.delay(
            user_id=str(current_user.id),
            limit=limit,
            offset=0
        )
        
        return APIResponse(
            success=True,
            data={
                "task_id": task_result.id,
                "status": "queued",
                "message": "Chat sync has been queued and will run in the background"
            },
            message=f"Chat synchronization started for up to {limit} chats"
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger chat sync for user {current_user.id}: {e}")
        return APIResponse(
            success=False,
            data={"status": "failed"},
            message="Failed to start chat synchronization. Please try again."
        )

@router.post("/messages/sync", response_model=APIResponse[dict])
async def sync_messages(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: UserResponse = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Trigger syncing of messages from saved Telegram chats to the database.
    
    This endpoint triggers a background task to fetch recent messages from
    all saved chats and store them in the database for the feed.
    """
    try:
        # Import the task here to avoid circular imports
        from app.tasks.tasks import check_for_new_posts_and_generate_drafts
        
        # Trigger the background task
        task_result = check_for_new_posts_and_generate_drafts.delay()
        
        return APIResponse(
            success=True,
            data={
                "task_id": task_result.id,
                "status": "queued",
                "message": "Message sync has been queued and will run in the background"
            },
            message="Message synchronization started for saved chats"
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger message sync for user {current_user.id}: {e}")
        return APIResponse(
            success=False,
            data={"status": "failed"},
            message="Failed to start message synchronization. Please try again."
        )


class BackfillRequest(BaseModel):
    dialogs_limit: int = Field(default=50, ge=1, le=200)
    per_dialog_messages: int = Field(default=50, ge=1, le=200)


@router.post("/messages/backfill", response_model=APIResponse[dict])
async def backfill_messages(
    body: BackfillRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> APIResponse[dict]:
    """Trigger a deeper historical backfill to increase feed pages.

    This dispatches a Celery task that scans more dialogs and messages per dialog.
    """
    try:
        from app.tasks.tasks import generate_drafts_for_user_recent_posts
        task = generate_drafts_for_user_recent_posts.delay(
            user_id=str(current_user.id),
            dialogs_limit=body.dialogs_limit,
            per_dialog_messages=body.per_dialog_messages,
        )
        return APIResponse(success=True, data={"task_id": task.id}, message="Backfill queued")
    except Exception as e:
        logger.error("Failed to queue backfill: %s", e)
        return APIResponse(success=False, data={"status": "failed"}, message="Failed to queue backfill")


@router.post("/reset-and-seed", response_model=APIResponse[dict])
async def reset_and_seed(
    current_user: UserResponse = Depends(get_current_user),
    source: str = Query("channels"),
):
    """Purge user's telegram data and reseed minimal baseline for the active session."""
    try:
        from app.tasks.tasks import reset_and_seed_user_data
        reset_and_seed_user_data.delay(user_id=str(current_user.id), chats_limit=current_user.telegram_chats_load_limit or 20, per_chat_limit=current_user.telegram_messages_load_limit or 50, source=source)
        return APIResponse(success=True, data={"status": "queued"}, message="Reset and seed queued")
    except Exception as e:
        return APIResponse(success=False, data={"status": "failed"}, message=str(e))

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
        # Keep only chats where commenting is possible for channels; include groups/supergroups and DMs
        def _allow(chat: dict) -> bool:
            t = str(chat.get("type") or "")
            if t == "channel":
                return bool(chat.get("comments_enabled", False))
            # groups/supergroups/private are fine
            return True
        chats_data = [c for c in chats_data or [] if _allow(c)]
        
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

@router.get("/chats/{chat_id}")
async def get_chat_details(
    chat_id: int,
    limit: int = Query(default=100, ge=1, le=200),
    current_user: UserResponse = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """Get details and messages for a specific chat."""
    try:
        telegram_service = container.telegram_service()
        client = await telegram_service.get_or_create_client(str(current_user.id))

        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No valid Telegram session found.",
            )

        # Fetch chat details
        try:
            chat_entity = await client.get_entity(chat_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat with ID {chat_id} not found.",
            )

        # Fetch messages
        messages_iter = client.iter_messages(chat_id, limit=limit)
        messages_data = [
            {
                "id": m.id,
                "text": m.text,
                "date": m.date,
                "sender_id": m.sender_id,
            }
            for m in await messages_iter.to_list() if m
        ]
        
        chat_data = {
            "id": chat_entity.id,
            "title": chat_entity.title,
            "type": "channel" if hasattr(chat_entity, 'megagroup') and chat_entity.megagroup else "user",
        }

        return APIResponse(
            success=True,
            data={"chat": chat_data, "messages": messages_data},
            message=f"Successfully retrieved chat {chat_id} and its messages.",
        )

    except HTTPException as http_exc:
        raise http_exc # Re-raise HTTPException
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"An error occurred while fetching chat details: {e}",
        ) 


@router.post("/chats/normalize-types")
async def normalize_chat_types(
    current_user: UserResponse = Depends(get_current_user),
):
    """Trigger background normalization of saved chat types for the current user."""
    try:
        from app.tasks.tasks import normalize_chat_types_for_user
        task = normalize_chat_types_for_user.delay(str(current_user.id))
        return APIResponse(success=True, data={"task_id": task.id}, message="Normalization queued")
    except Exception as e:
        return APIResponse(success=False, data=None, message=f"Failed to queue normalization: {e}")


# --- Dev helper: explicitly toggle comments_enabled for a chat ---
@router.post("/chats/set-comments-enabled")
async def dev_set_comments_enabled(
    telegram_id: int = Query(..., description="Telegram chat/channel id (can be negative -100 form or short id)"),
    enabled: bool = Query(...),
    current_user: UserResponse = Depends(get_current_user),
):
    """DEV-ONLY: Flip comments_enabled for a saved chat for the current user.

    This is a synchronous, light DB update to quickly correct misclassified channels.
    Only enabled when IS_DEVELOP=true.
    """
    if not settings.IS_DEVELOP:
        return APIResponse(success=False, data=None, message="forbidden in production")
    try:
        from app.repositories.chat_repository import ChatRepository
        repo = container.resolve(ChatRepository)
        # Try both raw id and normalized -100 variant
        updated = await repo.set_comments_enabled(current_user.id, int(telegram_id), enabled)
        if not updated and str(abs(telegram_id)).startswith("100"):
            short = int(str(abs(telegram_id))[3:])
            updated = await repo.set_comments_enabled(current_user.id, short, enabled)
        if not updated and len(str(abs(telegram_id))) <= 10:
            # Try long form from short id
            long = int(f"100{int(telegram_id)}") * -1
            updated = await repo.set_comments_enabled(current_user.id, long, enabled)
        return APIResponse(success=bool(updated), data={"telegram_id": telegram_id, "enabled": enabled}, message=("updated" if updated else "not_found"))
    except Exception as e:
        return APIResponse(success=False, data=None, message=str(e))