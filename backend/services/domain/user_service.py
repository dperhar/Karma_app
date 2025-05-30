"""Service for user management operations."""

import logging
from typing import Optional
from datetime import datetime

from models.user.schemas import UserCreate, UserResponse, UserUpdate
from services.base.base_service import BaseService
from services.repositories.user_repository import UserRepository
from services.websocket_service import WebSocketService

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """Service class for user management."""

    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
        self.websocket_service = WebSocketService()

    async def _send_user_update_notification(
        self, user_id: str, event: str, data: dict
    ):
        """Send WebSocket notification about user data changes."""
        try:
            await self.websocket_service.send_user_notification(
                user_id=user_id, event=event, data=data
            )
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")
            # Don't raise the exception to prevent breaking the main flow

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user with the provided data."""
        user_dict = user_data.model_dump()
        db_user = await self.user_repository.create_user(**user_dict)
        user_response = UserResponse.model_validate(db_user)

        # Send notification about user creation
        await self._send_user_update_notification(
            user_id=user_response.id,
            event="user_created",
            data=user_response.model_dump(),
        )

        return user_response

    async def get_user(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID."""
        user = await self.user_repository.get_user(user_id)
        return UserResponse.model_validate(user) if user else None

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[UserResponse]:
        """Get user by Telegram ID."""
        user = await self.user_repository.get_user_by_telegram_id(telegram_id)
        return UserResponse.model_validate(user) if user else None

    async def update_user(
        self,
        user_id: str,
        user_data: UserUpdate,
    ) -> Optional[UserResponse]:
        """Update user data."""
        logger = logging.getLogger(__name__)
        logger.info(
            f"UserService.update_user called with: user_id={user_id}, user_data={user_data.model_dump()}"
        )

        update_data = user_data.model_dump(exclude_unset=True)
        logger.info(f"Calling repository.update_user with data: {update_data}")

        user = await self.user_repository.update_user(user_id=user_id, **update_data)

        if user:
            logger.info(f"User updated successfully: {user.id}")
            logger.info(
                f"User data: first_name={user.first_name}, last_name={user.last_name}, username={user.username}"
            )
            user_response = UserResponse.model_validate(user)

            # Send notification about user update
            await self._send_user_update_notification(
                user_id=user_id,
                event="user_updated",
                data=user_response.model_dump(exclude={"telegram_session_string"}, mode="json"),
            )

            return user_response
        else:
            logger.error(f"Failed to update user with id: {user_id}")
            return None

    async def get_users(self) -> list[UserResponse]:
        """Get all users."""
        users = await self.user_repository.get_users()
        return [UserResponse.model_validate(user) for user in users]

    async def update_user_tg_session(
        self, user_id: str, session_string: str
    ) -> Optional[UserResponse]:
        """Update user's Telegram session string."""
        user = await self.user_repository.update_user(
            user_id=user_id, telegram_session_string=session_string
        )
        if user:
            user_response = UserResponse.model_validate(user)
            await self._send_user_update_notification(
                user_id=user_id,
                event="user_updated",
                data=user_response.model_dump(exclude={"telegram_session_string"}, mode="json"),
            )
            return user_response
        return None

    async def update_user_from_telegram(
        self, user_id: str, telegram_user
    ) -> Optional[UserResponse]:
        """Update user data from Telegram user object after successful authorization."""
        try:
            # Extract data from Telegram user object
            update_data = {
                "first_name": telegram_user.first_name,
                "last_name": getattr(telegram_user, 'last_name', None),
                "username": getattr(telegram_user, 'username', None),
                "telegram_id": telegram_user.id,
                "last_telegram_auth_at": datetime.utcnow(),
            }
            
            logger.info(f"Updating user {user_id} with Telegram data: {update_data}")
            
            user = await self.user_repository.update_user(user_id=user_id, **update_data)
            
            if user:
                logger.info(f"User {user_id} updated successfully with Telegram data")
                user_response = UserResponse.model_validate(user)
                
                # Send notification about user update
                await self._send_user_update_notification(
                    user_id=user_id,
                    event="user_updated",
                    data=user_response.model_dump(exclude={"telegram_session_string"}, mode="json"),
                )
                
                return user_response
            else:
                logger.error(f"Failed to update user {user_id} with Telegram data")
                return None
                
        except Exception as e:
            logger.error(f"Error updating user {user_id} from Telegram: {e}")
            return None
