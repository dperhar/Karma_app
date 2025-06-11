#!/usr/bin/env python3
"""Minimal FastAPI app to test /users/me endpoint."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.schemas.base import APIResponse
from app.schemas.user import UserResponse
from app.dependencies import get_current_user

app = FastAPI(title="Test API")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/users/me", response_model=APIResponse[UserResponse])
async def get_user(
    current_user: UserResponse = Depends(get_current_user),
):
    """Get current user."""
    return APIResponse(
        success=True,
        data=current_user,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)