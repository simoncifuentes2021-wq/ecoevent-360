from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import LogisticsOrderStatus


class LogisticsOrderItemCreate(BaseModel):
    item_id: UUID
    quantity_requested: Decimal = Field(gt=0)
    notes: str | None = None

    @field_validator("notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class LogisticsOrderItemUpdate(BaseModel):
    quantity_requested: Decimal | None = Field(default=None, gt=0)
    notes: str | None = None

    @field_validator("notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class LogisticsOrderItemLoad(BaseModel):
    quantity_loaded: Decimal = Field(gt=0)
    notes: str | None = None

    @field_validator("notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class LogisticsOrderDispatch(BaseModel):
    dispatch_notes: str | None = None

    @field_validator("dispatch_notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class LogisticsOrderCreate(BaseModel):
    warehouse_id: UUID
    assigned_operator_id: UUID
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    delivery_zone: str | None = Field(default=None, max_length=180)
    delivery_notes: str | None = None
    items: list[LogisticsOrderItemCreate] = Field(min_length=1)

    @field_validator("title", "description", "delivery_zone", "delivery_notes", mode="before")
    @classmethod
    def clean_strings(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def validate_unique_items(self):
        item_ids = [item.item_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Inventory products cannot be duplicated in the same logistics order")
        return self


class LogisticsOrderUpdate(BaseModel):
    warehouse_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    delivery_zone: str | None = Field(default=None, max_length=180)
    delivery_notes: str | None = None
    status: LogisticsOrderStatus | None = None


class LogisticsOrderAssign(BaseModel):
    assigned_operator_id: UUID


class LogisticsOrderEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class LogisticsOrderWarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class LogisticsOrderUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str


class LogisticsOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    item_id: UUID
    item_name_snapshot: str
    item_type_snapshot: str
    unit_snapshot: str | None = None
    quantity_requested: Decimal
    quantity_reserved: Decimal
    quantity_missing: Decimal
    reservation_status: str | None = None
    quantity_loaded: Decimal
    quantity_dispatched: Decimal
    preparation_status: str
    unit_price_snapshot: Decimal
    total_price: Decimal
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class LogisticsOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    warehouse_id: UUID
    requested_by: UUID
    assigned_operator_id: UUID
    status: LogisticsOrderStatus
    title: str
    description: str | None = None
    delivery_zone: str | None = None
    delivery_notes: str | None = None
    total_estimated_amount: Decimal
    reserved_at: datetime | None = None
    reserved_by: UUID | None = None
    prepared_at: datetime | None = None
    prepared_by: UUID | None = None
    dispatched_at: datetime | None = None
    dispatched_by: UUID | None = None
    dispatch_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    event: LogisticsOrderEventRead | None = None
    warehouse: LogisticsOrderWarehouseRead | None = None
    requester: LogisticsOrderUserRead | None = None
    assigned_operator: LogisticsOrderUserRead | None = None
    items: list[LogisticsOrderItemRead] = []


class LogisticsOrderListResponse(BaseModel):
    items: list[LogisticsOrderRead]
    total: int
    page: int
    limit: int


class LogisticsOrderStockCheckItem(BaseModel):
    item_id: UUID
    item_name_snapshot: str
    quantity_requested: Decimal
    quantity_reserved: Decimal
    warehouse_id: UUID
    warehouse_name: str
    quantity_on_hand: Decimal
    quantity_reserved_in_stock: Decimal
    quantity_damaged: Decimal
    available_quantity: Decimal
    missing_quantity: Decimal
    can_reserve: bool


class LogisticsOrderStockCheckResponse(BaseModel):
    order_id: UUID
    status: LogisticsOrderStatus
    warehouse_id: UUID
    warehouse_name: str
    can_reserve_all: bool
    items: list[LogisticsOrderStockCheckItem]
