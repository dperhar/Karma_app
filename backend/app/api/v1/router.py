"""Main API router for v1."""

from fastapi import APIRouter

from . import auth, drafts, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["v1-authentication"])
api_router.include_router(users.router, prefix="/users", tags=["v1-users"])
api_router.include_router(drafts.router, prefix="/drafts", tags=["v1-drafts"]) 