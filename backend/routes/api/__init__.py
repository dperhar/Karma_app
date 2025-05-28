"""API routes."""

from fastapi import APIRouter

from routes.api import menu, users

api_router = APIRouter()

api_router.include_router(menu.router)
api_router.include_router(users.router)
