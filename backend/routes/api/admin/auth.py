"""Admin routes."""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends

from config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_SECRET_KEY
from models.user.schemas import AdminCreate, AdminLogin, AdminResponse
from services.dependencies import get_admin_service
from services.domain.admin_service import AdminService

router = APIRouter(prefix="/auth")


@router.post("/login")
async def login_admin(
    login_data: AdminLogin,
    admin_service: AdminService = Depends(get_admin_service),
):
    """Login admin."""
    admin = await admin_service.authenticate_admin(login_data)

    # Generate token
    token_data = admin.model_dump()
    token_data["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm="HS256")

    return {"admin": admin, "token": token}


@router.post("/create", response_model=AdminResponse)
async def create_admin(
    admin_data: AdminCreate,
    admin_service: AdminService = Depends(get_admin_service),
):
    """Create new admin."""
    return await admin_service.create_admin(admin_data)
