"""API routes for user management."""

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.schemas.base import APIResponse
from app.schemas.user import UserResponse
from app.dependencies import logger, get_current_admin
from app.core.dependencies import get_user_service
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=APIResponse[list[UserResponse]])
async def get_users(
    user_service: UserService = Depends(get_user_service),
) -> APIResponse[list[UserResponse]]:
    """Get all users."""
    try:
        users = await user_service.get_users()
        if not users:
            return APIResponse(success=True, data=[], message="No users found")

        return APIResponse(
            success=True, data=users, message="Users retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error retrieving users: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving users",
        ) from e


@router.post("/import", response_model=APIResponse[list[UserResponse]])
async def import_users(
    file: UploadFile = File(...),
    user_service: UserService = Depends(get_user_service),
) -> APIResponse[list[UserResponse]]:
    """Import users from Excel file."""
    try:
        imported_users = await user_service.import_users_from_excel(file)
        return APIResponse(
            success=True, data=imported_users, message="Users successfully imported"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Error importing users: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error importing users",
        ) from e


@router.get("/export")
async def export_users(
    user_service: UserService = Depends(get_user_service),
) -> Response:
    """Export users to Excel file."""
    try:
        excel_data = await user_service.export_users_to_excel()
        if not excel_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data available for export",
            )

        filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"Error exporting users: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error exporting users",
        ) from e
