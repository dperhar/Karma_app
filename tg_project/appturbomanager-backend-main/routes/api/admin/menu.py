"""API routes for menu item management."""

from fastapi import APIRouter, Depends, HTTPException, status

from models.base.schemas import APIResponse, MenuItemCreate, MenuItemResponse
from routes.dependencies import logger
from services.dependencies import get_menu_service
from services.domain.menu_service import MenuService

router = APIRouter(prefix="/menu", tags=["menu"])


@router.post("", response_model=APIResponse[MenuItemResponse])
async def create_menu_item(
    menu_item_data: MenuItemCreate,
    menu_service: MenuService = Depends(get_menu_service),
) -> APIResponse[MenuItemResponse]:
    """Create a new menu item."""
    try:
        menu_item = await menu_service.create_menu_item(menu_item_data)
        return APIResponse(
            success=True,
            data=menu_item,
            message="Menu item created successfully",
        )
    except Exception as e:
        logger.error(f"Error creating menu item: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create menu item",
        ) from e


@router.get("", response_model=APIResponse[list[MenuItemResponse]])
async def get_menu_items(
    menu_service: MenuService = Depends(get_menu_service),
) -> APIResponse[list[MenuItemResponse]]:
    """Get all menu items."""
    try:
        menu_items = await menu_service.get_menu_items()
        return APIResponse(
            success=True,
            data=menu_items,
            message="Menu items retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Error retrieving menu items: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve menu items",
        ) from e


@router.get("/{menu_item_id}", response_model=APIResponse[MenuItemResponse])
async def get_menu_item(
    menu_item_id: str,
    menu_service: MenuService = Depends(get_menu_service),
) -> APIResponse[MenuItemResponse]:
    """Get menu item by ID."""
    try:
        menu_item = await menu_service.get_menu_item(menu_item_id)
        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu item with ID {menu_item_id} not found",
            )
        return APIResponse(
            success=True,
            data=menu_item,
            message="Menu item retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving menu item: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve menu item",
        ) from e


@router.put("/{menu_item_id}", response_model=APIResponse[MenuItemResponse])
async def update_menu_item(
    menu_item_id: str,
    menu_item_data: MenuItemCreate,
    menu_service: MenuService = Depends(get_menu_service),
) -> APIResponse[MenuItemResponse]:
    """Update menu item by ID."""
    try:
        menu_item = await menu_service.update_menu_item(menu_item_id, menu_item_data)
        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu item with ID {menu_item_id} not found",
            )
        return APIResponse(
            success=True,
            data=menu_item,
            message="Menu item updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating menu item: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update menu item",
        ) from e


@router.delete("/{menu_item_id}", response_model=APIResponse)
async def delete_menu_item(
    menu_item_id: str,
    menu_service: MenuService = Depends(get_menu_service),
) -> APIResponse:
    """Delete menu item by ID."""
    try:
        await menu_service.delete_menu_item(menu_item_id)
        return APIResponse(
            success=True,
            message="Menu item deleted successfully",
        )
    except Exception as e:
        logger.error(f"Error deleting menu item: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete menu item",
        ) from e
