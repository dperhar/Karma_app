"""Admin API routes."""

from fastapi import APIRouter

from routes.api.admin import (
    auth,
    menu,
    messages,
    users,
)

router = APIRouter(prefix="/admin")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(menu.router)
router.include_router(messages.router)
