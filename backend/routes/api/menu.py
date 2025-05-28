"""API routes for menu items."""

from fastapi import APIRouter, Depends, HTTPException, status

from models.base.schemas import APIResponse, MenuItemResponse
from services.dependencies import get_menu_service
from services.domain.menu_service import MenuService

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/items", response_model=APIResponse[list[MenuItemResponse]])
async def get_menu_items(
    menu_service: MenuService = Depends(get_menu_service),
) -> APIResponse[list[MenuItemResponse]]:
    """Get all active menu items."""
    try:
        items = await menu_service.get_menu_items()
        return APIResponse(success=True, data=items)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
