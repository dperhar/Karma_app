"""Repository for user management operations."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models.user.user import User
from services.base.base_repository import BaseRepository


class UserRepository(BaseRepository):
    """Repository class for user management."""

    async def create_user(self, **user_data) -> Optional[User]:
        """Create a new user."""
        async with self.get_session() as session:
            try:
                self.logger.info("Creating user with data: %s", user_data)
                user = User(**user_data)

                session.add(user)
                await session.commit()
                await session.refresh(user)

                self.logger.info("User created successfully with id: %s", user.id)
                return user
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error creating user: %s", str(e), exc_info=True)
                raise

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        async with self.get_session() as session:
            try:
                query = select(User).where(User.id == user_id)
                result = await session.execute(query)
                user = result.unique().scalar_one_or_none()
                if not user:
                    self.logger.info("User not found with id: %s", user_id)
                return user
            except SQLAlchemyError as e:
                self.logger.error("Error getting user: %s", str(e), exc_info=True)
                raise

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        async with self.get_session() as session:
            try:
                query = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(query)
                user = result.unique().scalar_one_or_none()
                if not user:
                    self.logger.info("User not found with telegram_id: %s", telegram_id)
                return user
            except SQLAlchemyError as e:
                self.logger.error("Error getting user: %s", str(e), exc_info=True)
                raise

    async def update_user(self, user_id: str, **update_data) -> Optional[User]:
        """Update user data."""
        async with self.get_session() as session:
            try:
                query = select(User).where(User.id == user_id)
                result = await session.execute(query)
                user = result.unique().scalar_one_or_none()

                if user:
                    for key, value in update_data.items():
                        setattr(user, key, value)
                    await session.commit()
                    await session.refresh(user)
                    self.logger.info("User updated successfully: %s", user_id)
                else:
                    self.logger.info("User not found with id: %s", user_id)

                return user
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error updating user: %s", str(e), exc_info=True)
                raise

    async def get_users(self) -> list[User]:
        """Get all users."""
        async with self.get_session() as session:
            try:
                query = select(User)
                result = await session.execute(query)
                users = result.unique().scalars().all()
                return list(users)
            except SQLAlchemyError as e:
                self.logger.error("Error getting users: %s", str(e), exc_info=True)
                raise
