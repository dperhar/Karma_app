"""Service for admin management operations."""

from typing import Optional

from fastapi import HTTPException, status

from models.user.schemas import AdminCreate, AdminLogin, AdminResponse
from services.base.base_service import BaseService
from services.repositories.admin_repository import AdminRepository


class AdminService(BaseService):
    """Service class for admin management."""

    def __init__(self, admin_repository: AdminRepository):
        super().__init__()
        self.admin_repository = admin_repository

    async def create_admin(self, admin_data: AdminCreate) -> AdminResponse:
        """Create a new admin with the provided data."""
        admin_dict = admin_data.model_dump()
        db_admin = await self.admin_repository.create_admin(**admin_dict)
        return AdminResponse.model_validate(db_admin)

    async def authenticate_admin(
        self, login_data: AdminLogin
    ) -> Optional[AdminResponse]:
        """Authenticate admin with login and password."""
        admin = await self.admin_repository.get_admin_by_login(login_data.login)
        if not admin or not admin.check_password(login_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login or password",
            )
        return AdminResponse.model_validate(admin)
