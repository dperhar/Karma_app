"""Pydantic schemas for user data validation and serialization."""

from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

from app.models.menu import MenuItemStatus
from app.models.message import MessageStatus

# Generic type for response data
DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    """Generic schema for standardized API responses."""

    success: bool
    data: Optional[DataT] = None
    message: Optional[str] = None


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""

    page: int = 1
    per_page: int = 10


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Schema for paginated responses."""

    items: list[DataT]
    total: int
    page: int
    per_page: int
    pages: int


# MenuItem schemas
class MenuItemBase(BaseModel):
    """Base schema for MenuItem."""

    title: str
    url: str
    order: int
    status: MenuItemStatus


class MenuItemCreate(MenuItemBase):
    """Schema for creating a new MenuItem."""

    pass


class MenuItemUpdate(BaseModel):
    """Schema for updating an existing MenuItem."""

    title: Optional[str] = None
    url: Optional[str] = None
    order: Optional[int] = None
    status: Optional[MenuItemStatus] = None


class MenuItemResponse(MenuItemBase):
    """Schema for MenuItem response."""

    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Message schemas
class MessageBase(BaseModel):
    """Base schema for Message."""

    text: str
    status: MessageStatus


class MessageCreate(MessageBase):
    """Schema for creating a new Message."""

    pass


class MessageUpdate(BaseModel):
    """Schema for updating an existing Message."""

    text: Optional[str] = None
    status: Optional[MessageStatus] = None


class MessageStatusUpdate(BaseModel):
    """Schema for updating only the status of a Message."""

    status: MessageStatus


class MessageResponse(MessageBase):
    """Schema for Message response."""

    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
