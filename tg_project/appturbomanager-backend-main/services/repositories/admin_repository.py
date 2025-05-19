"""Repository for admin management operations."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models.user.admin import Admin
from services.base.base_repository import BaseRepository


class AdminRepository(BaseRepository):
    """Repository class for admin management."""

    async def create_admin(self, **admin_data) -> Optional[Admin]:
        """Create a new admin."""
        async with self.get_session() as session:
            try:
                self.logger.info("Creating admin with data: %s", admin_data)
                password = admin_data.pop("password")
                admin = Admin(**admin_data)
                admin.set_password(password)

                session.add(admin)
                await session.commit()
                await session.refresh(admin)

                self.logger.info("Admin created successfully with id: %s", admin.id)
                return admin
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error creating admin: %s", str(e), exc_info=True)
                raise

    async def get_admin_by_login(self, login: str) -> Optional[Admin]:
        """Get admin by login."""
        async with self.get_session() as session:
            try:
                query = select(Admin).where(Admin.login == login)
                result = await session.execute(query)
                admin = result.unique().scalar_one_or_none()
                if not admin:
                    self.logger.info("Admin not found with login: %s", login)
                return admin
            except SQLAlchemyError as e:
                self.logger.error("Error getting admin: %s", str(e), exc_info=True)
                raise
