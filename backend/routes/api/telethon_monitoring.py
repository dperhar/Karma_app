"""API endpoints for monitoring refactored Telethon service."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from services.external.telethon.refactored_client_service import RefactoredTelethonClientService
from services.dependencies import container

router = APIRouter(prefix="/api/telethon", tags=["telethon-monitoring"])


@router.get("/health")
async def get_telethon_health() -> Dict[str, Any]:
    """Get comprehensive health report for Telethon service."""
    try:
        service = container.resolve(RefactoredTelethonClientService)
        health_report = await service.get_health_report()
        return {
            "status": "healthy",
            "health_report": health_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting health report: {str(e)}")


@router.get("/stats")
async def get_telethon_stats() -> Dict[str, Any]:
    """Get comprehensive statistics for Telethon service."""
    try:
        service = container.resolve(RefactoredTelethonClientService)
        stats = await service.get_service_stats()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@router.post("/cleanup/sessions")
async def cleanup_invalid_sessions() -> Dict[str, str]:
    """Cleanup invalid sessions."""
    try:
        service = container.resolve(RefactoredTelethonClientService)
        await service.cleanup_invalid_sessions()
        return {
            "status": "success",
            "message": "Invalid sessions cleaned up"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up sessions: {str(e)}")


@router.get("/connections/{user_id}/status")
async def get_user_connection_status(user_id: str) -> Dict[str, Any]:
    """Get connection status for specific user."""
    try:
        service = container.resolve(RefactoredTelethonClientService)
        
        # Check if user has valid session
        has_session = await service.validate_user_session(user_id)
        
        # Try to get client (without creating new connection)
        client = await service.get_client(user_id) if has_session else None
        
        return {
            "user_id": user_id,
            "has_valid_session": has_session,
            "has_active_connection": client is not None,
            "status": "connected" if client else "disconnected"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting connection status: {str(e)}")


@router.delete("/connections/{user_id}")
async def disconnect_user(user_id: str) -> Dict[str, str]:
    """Disconnect specific user."""
    try:
        service = container.resolve(RefactoredTelethonClientService)
        await service.disconnect_client(user_id)
        return {
            "status": "success",
            "message": f"User {user_id} disconnected"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting user: {str(e)}")


@router.post("/service/start")
async def start_service() -> Dict[str, str]:
    """Start the refactored Telethon service."""
    try:
        service = container.resolve(RefactoredTelethonClientService)
        await service.start()
        return {
            "status": "success",
            "message": "Refactored Telethon service started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting service: {str(e)}")


@router.post("/service/stop")
async def stop_service() -> Dict[str, str]:
    """Stop the refactored Telethon service."""
    try:
        service = container.resolve(RefactoredTelethonClientService)
        await service.stop()
        return {
            "status": "success",
            "message": "Refactored Telethon service stopped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping service: {str(e)}") 