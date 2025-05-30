"""Service for menu item management operations."""

from typing import Optional

from models.base.schemas import MenuItemCreate, MenuItemResponse
from services.base.base_service import BaseService
from services.repositories.menu_repository import MenuRepository


class MenuService(BaseService):
    """Service class for menu item management."""

    def __init__(self, menu_repository: MenuRepository):
        super().__init__()
        self.menu_repository = menu_repository

    async def create_menu_item(
        self, menu_item_data: MenuItemCreate
    ) -> MenuItemResponse:
        """Create a new menu item with the provided data."""
        menu_item_dict = menu_item_data.model_dump()
        db_menu_item = await self.menu_repository.create_menu_item(**menu_item_dict)
        return MenuItemResponse.model_validate(db_menu_item)

    async def get_menu_item(self, menu_item_id: str) -> Optional[MenuItemResponse]:
        """Get menu item by ID."""
        menu_item = await self.menu_repository.get_menu_item(menu_item_id)
        return MenuItemResponse.model_validate(menu_item) if menu_item else None

    async def update_menu_item(
        self, menu_item_id: str, menu_item_data: MenuItemCreate
    ) -> Optional[MenuItemResponse]:
        """Update menu item data."""
        menu_item_dict = menu_item_data.model_dump()
        menu_item = await self.menu_repository.update_menu_item(
            menu_item_id, **menu_item_dict
        )
        return MenuItemResponse.model_validate(menu_item) if menu_item else None

    async def delete_menu_item(self, menu_item_id: str) -> None:
        """Delete menu item by ID."""
        await self.menu_repository.delete_menu_item(menu_item_id)

    async def get_menu_items(self) -> list[MenuItemResponse]:
        """Get all menu items."""
        menu_items = await self.menu_repository.get_menu_items()
        return [MenuItemResponse.model_validate(menu_item) for menu_item in menu_items]

    async def get_active_menu_items(self) -> list[MenuItemResponse]:
        """Get all active menu items."""
        menu_items = await self.menu_repository.get_active_menu_items()
        return [MenuItemResponse.model_validate(menu_item) for menu_item in menu_items]
