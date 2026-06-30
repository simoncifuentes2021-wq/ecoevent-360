from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    address: str | None = None
    city: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    address: str | None = None
    city: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    is_active: bool | None = None


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str | None = None
    city: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WarehouseListResponse(BaseModel):
    items: list[WarehouseRead]
    total: int
    page: int
    limit: int


class WarehouseUserCreate(BaseModel):
    user_id: UUID
    can_view_stock: bool = True
    can_manage_stock: bool = False
    can_dispatch_orders: bool = True


class WarehouseUserUpdate(BaseModel):
    can_view_stock: bool | None = None
    can_manage_stock: bool | None = None
    can_dispatch_orders: bool | None = None


class WarehouseUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    warehouse_id: UUID
    user_id: UUID
    can_view_stock: bool
    can_manage_stock: bool
    can_dispatch_orders: bool
    created_at: datetime
    user_full_name: str | None = None
    user_email: str | None = None
    user_role: UserRole | None = None


class MyWarehouseAssignmentRead(BaseModel):
    id: UUID
    warehouse_id: UUID
    warehouse_name: str
    can_view_stock: bool
    can_manage_stock: bool
    can_dispatch_orders: bool
    created_at: datetime
