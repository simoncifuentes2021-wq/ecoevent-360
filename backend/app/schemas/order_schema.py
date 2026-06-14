from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import OrderEvidenceStage, OrderItemStageStatus, OrderStatus, UserRole


class CatalogItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    category: str | None = Field(default=None, max_length=120)
    description: str | None = None
    unit: str | None = Field(default=None, max_length=50)
    default_unit_price: Decimal | None = Field(default=Decimal("0"), ge=0)
    is_active: bool = True

    @field_validator("name", "category", "description", "unit", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class CatalogItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    category: str | None = Field(default=None, max_length=120)
    description: str | None = None
    unit: str | None = Field(default=None, max_length=50)
    default_unit_price: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("name", "category", "description", "unit", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class CatalogItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str | None = None
    description: str | None = None
    unit: str | None = None
    default_unit_price: Decimal | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CatalogItemListResponse(BaseModel):
    items: list[CatalogItemRead]
    total: int
    page: int
    limit: int


class OrderUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    role: UserRole


class OrderEventClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_name: str


class OrderEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    client_id: UUID
    client: OrderEventClientRead | None = None


class OrderProgressRead(BaseModel):
    total_items: int
    loaded_items: int
    delivered_items: int
    returned_items: int
    load_progress_percentage: int
    delivery_progress_percentage: int
    return_progress_percentage: int


class EventOrderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    assigned_to: UUID | None = None
    requested_date: datetime | None = None
    required_date: datetime | None = None
    notes: str | None = None

    @field_validator("title", "description", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class EventOrderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    assigned_to: UUID | None = None
    requested_date: datetime | None = None
    required_date: datetime | None = None
    notes: str | None = None

    @field_validator("title", "description", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class EventOrderStatusUpdate(BaseModel):
    status: OrderStatus


class EventOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    requested_by: UUID | None = None
    assigned_to: UUID | None = None
    title: str
    description: str | None = None
    status: OrderStatus
    requested_date: datetime | None = None
    required_date: datetime | None = None
    total_amount: Decimal | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    event: OrderEventRead | None = None
    assignee: OrderUserRead | None = None
    progress: OrderProgressRead
    items: list[EventOrderItemRead] = []


class EventOrderListResponse(BaseModel):
    items: list[EventOrderRead]
    total: int
    page: int
    limit: int


class EventOrderItemCreate(BaseModel):
    catalog_item_id: UUID | None = None
    zone_id: UUID | None = None
    item_name_snapshot: str | None = Field(default=None, max_length=180)
    quantity: Decimal = Field(gt=0)
    unit: str | None = Field(default=None, max_length=50)
    unit_price: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None

    @field_validator("item_name_snapshot", "unit", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class EventOrderItemUpdate(BaseModel):
    catalog_item_id: UUID | None = None
    zone_id: UUID | None = None
    item_name_snapshot: str | None = Field(default=None, min_length=1, max_length=180)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=50)
    unit_price: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None

    @field_validator("item_name_snapshot", "unit", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class EventOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    catalog_item_id: UUID | None = None
    zone_id: UUID | None = None
    item_name_snapshot: str
    quantity: Decimal
    unit: str | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    notes: str | None = None
    load_status: OrderItemStageStatus
    delivery_status: OrderItemStageStatus
    return_status: OrderItemStageStatus
    loaded_at: datetime | None = None
    delivered_at: datetime | None = None
    returned_at: datetime | None = None
    loaded_by: UUID | None = None
    delivered_by: UUID | None = None
    returned_by: UUID | None = None
    load_observation: str | None = None
    delivery_observation: str | None = None
    return_observation: str | None = None
    created_at: datetime
    updated_at: datetime


class EventOrderDetailRead(EventOrderRead):
    pass


class OrderItemStageUpdate(BaseModel):
    status: OrderItemStageStatus = OrderItemStageStatus.COMPLETED
    observation: str | None = None

    @field_validator("observation", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class OrderEvidenceCreate(BaseModel):
    stage: OrderEvidenceStage
    order_item_id: UUID | None = None
    description: str | None = None
    visible_to_client: bool = False


class OrderEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    order_id: UUID
    order_item_id: UUID | None = None
    uploaded_by: UUID | None = None
    stage: OrderEvidenceStage
    file_url: str
    file_type: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    description: str | None = None
    visible_to_client: bool
    created_at: datetime
