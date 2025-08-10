"""Main API v1 router."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.drafts import router as drafts_router
from app.api.v1.feed import router as feed_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.users import router as users_router

api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(drafts_router, prefix="/drafts", tags=["drafts"])
api_router.include_router(feed_router, prefix="/feed", tags=["feed"])
api_router.include_router(telegram_router, prefix="/telegram", tags=["telegram"])


# Health check endpoint
@api_router.get("/health")
def health_check():
    """API root endpoint."""
    return {"message": "Karma App API v1"} 