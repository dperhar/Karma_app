"""Repository for menu item management operations."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models.base.menu import MenuItem, MenuItemStatus
from services.base.base_repository import BaseRepository


class MenuRepository(BaseRepository):
    """Repository class for menu item management."""

    async def create_menu_item(self, **menu_item_data) -> Optional[MenuItem]:
        """Create a new menu item."""
        async with self.get_session() as session:
            try:
                self.logger.info("Creating menu item with data: %s", menu_item_data)
                menu_item = MenuItem(**menu_item_data)
                session.add(menu_item)
                await session.commit()
                await session.refresh(menu_item)
                self.logger.info(
                    "Menu item created successfully with id: %s", menu_item.id
                )
                return menu_item
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error creating menu item: %s", str(e), exc_info=True)
                raise

    async def get_menu_item(self, menu_item_id: str) -> Optional[MenuItem]:
        """Get menu item by ID."""
        async with self.get_session() as session:
            try:
                query = select(MenuItem).where(MenuItem.id == menu_item_id)
                result = await session.execute(query)
                menu_item = result.scalar_one_or_none()
                if not menu_item:
                    self.logger.info("Menu item not found with id: %s", menu_item_id)
                return menu_item
            except SQLAlchemyError as e:
                self.logger.error("Error getting menu item: %s", str(e), exc_info=True)
                raise

    async def update_menu_item(
        self, menu_item_id: str, **update_data
    ) -> Optional[MenuItem]:
        """Update menu item data."""
        async with self.get_session() as session:
            try:
                menu_item = await session.get(MenuItem, menu_item_id)
                if not menu_item:
                    self.logger.info("Menu item not found with id: %s", menu_item_id)
                    return None

                for key, value in update_data.items():
                    if hasattr(menu_item, key):
                        setattr(menu_item, key, value)

                await session.commit()
                await session.refresh(menu_item)
                self.logger.info("Menu item updated successfully: %s", menu_item_id)
                return menu_item
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error updating menu item: %s", str(e), exc_info=True)
                raise

    async def delete_menu_item(self, menu_item_id: str) -> None:
        """Delete menu item by ID."""
        async with self.get_session() as session:
            try:
                menu_item = await session.get(MenuItem, menu_item_id)
                if menu_item:
                    await session.delete(menu_item)
                    await session.commit()
                    self.logger.info("Menu item deleted successfully: %s", menu_item_id)
                else:
                    self.logger.info(
                        "Menu item not found for deletion: %s", menu_item_id
                    )
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error deleting menu item: %s", str(e), exc_info=True)
                raise

    async def get_menu_items(self) -> list[MenuItem]:
        """Get all menu items."""
        async with self.get_session() as session:
            query = select(MenuItem).order_by(MenuItem.order)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_active_menu_items(self) -> list[MenuItem]:
        """Get all active menu items."""
        async with self.get_session() as session:
            query = (
                select(MenuItem)
                .where(MenuItem.status == MenuItemStatus.ACTIVE)
                .order_by(MenuItem.order)
            )
            result = await session.execute(query)
            return result.scalars().all()
