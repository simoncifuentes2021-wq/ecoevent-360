from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import PurchaseDeliveryMode, PurchaseRequestStatus


def validate_whole_quantity(value: Decimal) -> Decimal:
    if value != value.to_integral_value():
        raise ValueError("Quantity must be a whole number")
    return value


class PurchaseRequestItemCreate(BaseModel):
    item_id: UUID
    quantity_requested: Decimal = Field(gt=0)
    unit_price_estimated: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = None

    @field_validator("quantity_requested")
    @classmethod
    def quantity_must_be_whole(cls, value: Decimal) -> Decimal:
        return validate_whole_quantity(value)


class PurchaseRequestCreate(BaseModel):
    event_id: UUID | None = None
    logistics_order_id: UUID | None = None
    warehouse_id: UUID | None = None
    delivery_mode: PurchaseDeliveryMode = PurchaseDeliveryMode.TO_WAREHOUSE
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    notes: str | None = None
    items: list[PurchaseRequestItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_delivery_mode(self):
        if self.delivery_mode == PurchaseDeliveryMode.TO_WAREHOUSE and self.warehouse_id is None:
            raise ValueError("warehouse_id is required for TO_WAREHOUSE purchases")
        return self


class PurchaseRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    notes: str | None = None
    warehouse_id: UUID | None = None


class PurchaseRequestFromOrderCreate(BaseModel):
    title: str = Field(default="Compra por faltante de stock", min_length=1, max_length=180)
    delivery_mode: PurchaseDeliveryMode = PurchaseDeliveryMode.TO_WAREHOUSE
    warehouse_id: UUID | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_delivery_mode(self):
        if self.delivery_mode == PurchaseDeliveryMode.TO_WAREHOUSE and self.warehouse_id is None:
            raise ValueError("warehouse_id is required for TO_WAREHOUSE purchases")
        return self


class PurchaseRequestReject(BaseModel):
    rejection_reason: str = Field(min_length=1)


class PurchaseRequestMarkPurchasedItem(BaseModel):
    purchase_request_item_id: UUID
    quantity_purchased: Decimal = Field(gt=0)
    unit_price_purchased: Decimal = Field(ge=0)

    @field_validator("quantity_purchased")
    @classmethod
    def quantity_must_be_whole(cls, value: Decimal) -> Decimal:
        return validate_whole_quantity(value)


class PurchaseRequestMarkPurchased(BaseModel):
    items: list[PurchaseRequestMarkPurchasedItem] = Field(min_length=1)
    notes: str | None = None


class PurchaseRequestReceiveItem(BaseModel):
    purchase_request_item_id: UUID
    quantity_received: Decimal = Field(gt=0)

    @field_validator("quantity_received")
    @classmethod
    def quantity_must_be_whole(cls, value: Decimal) -> Decimal:
        return validate_whole_quantity(value)


class PurchaseRequestReceive(BaseModel):
    items: list[PurchaseRequestReceiveItem] = Field(min_length=1)
    notes: str | None = None


class PurchaseEntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None = None
    title: str | None = None
    full_name: str | None = None
    email: str | None = None


class PurchaseRequestItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purchase_request_id: UUID
    logistics_order_item_id: UUID | None = None
    item_id: UUID
    item_name_snapshot: str
    unit_snapshot: str | None = None
    quantity_requested: Decimal
    quantity_purchased: Decimal
    quantity_received: Decimal
    unit_price_estimated: Decimal
    unit_price_purchased: Decimal
    total_estimated: Decimal
    total_purchased: Decimal
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class PurchaseRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID | None = None
    logistics_order_id: UUID | None = None
    requested_by: UUID | None = None
    approved_by: UUID | None = None
    purchased_by: UUID | None = None
    received_by: UUID | None = None
    warehouse_id: UUID | None = None
    status: PurchaseRequestStatus
    delivery_mode: PurchaseDeliveryMode
    title: str
    description: str | None = None
    notes: str | None = None
    rejection_reason: str | None = None
    requested_at: datetime
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    purchased_at: datetime | None = None
    received_at: datetime | None = None
    cancelled_at: datetime | None = None
    total_estimated_amount: Decimal
    total_purchased_amount: Decimal
    created_at: datetime
    updated_at: datetime
    event: PurchaseEntityRead | None = None
    logistics_order: PurchaseEntityRead | None = None
    warehouse: PurchaseEntityRead | None = None
    requester: PurchaseEntityRead | None = None
    approver: PurchaseEntityRead | None = None
    purchaser: PurchaseEntityRead | None = None
    receiver: PurchaseEntityRead | None = None
    items: list[PurchaseRequestItemRead] = Field(default_factory=list)


class PurchaseRequestListResponse(BaseModel):
    items: list[PurchaseRequestRead]
    total: int
    page: int
    limit: int
