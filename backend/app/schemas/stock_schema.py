from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import InventoryItemType, StockMovementType


class StockBalanceBase(BaseModel):
    warehouse_id: UUID
    item_id: UUID
    quantity_on_hand: Decimal = Field(default=Decimal("0"), ge=0)
    quantity_reserved: Decimal = Field(default=Decimal("0"), ge=0)
    quantity_damaged: Decimal = Field(default=Decimal("0"), ge=0)

    @model_validator(mode="after")
    def validate_quantities(self):
        if self.quantity_reserved > self.quantity_on_hand:
            raise ValueError("quantity_reserved cannot be greater than quantity_on_hand")
        if self.quantity_damaged > self.quantity_on_hand:
            raise ValueError("quantity_damaged cannot be greater than quantity_on_hand")
        if self.quantity_on_hand - self.quantity_reserved - self.quantity_damaged < 0:
            raise ValueError("available_quantity cannot be negative")
        return self


class StockBalanceCreate(StockBalanceBase):
    pass


class StockBalanceUpdate(BaseModel):
    quantity_on_hand: Decimal | None = Field(default=None, ge=0)
    quantity_reserved: Decimal | None = Field(default=None, ge=0)
    quantity_damaged: Decimal | None = Field(default=None, ge=0)


class StockBalanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    warehouse_id: UUID
    warehouse_name: str
    item_id: UUID
    item_name: str
    item_type: InventoryItemType
    unit: str | None = None
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_damaged: Decimal
    available_quantity: Decimal
    min_stock: Decimal
    is_low_stock: bool
    unit_price: Decimal
    estimated_stock_value: Decimal
    created_at: datetime
    updated_at: datetime


class StockBalanceListResponse(BaseModel):
    items: list[StockBalanceRead]
    total: int
    page: int
    limit: int


class StockMovementCreate(BaseModel):
    warehouse_id: UUID
    item_id: UUID
    movement_type: StockMovementType
    quantity: Decimal = Field(gt=0)
    quantity_on_hand: Decimal | None = Field(default=None, ge=0)
    quantity_reserved: Decimal | None = Field(default=None, ge=0)
    quantity_damaged: Decimal | None = Field(default=None, ge=0)
    reference_type: str | None = Field(default=None, max_length=80)
    reference_id: UUID | None = None
    reason: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_correction_reason(self):
        if self.movement_type in {
            StockMovementType.CORRECTION,
            StockMovementType.LOSS,
            StockMovementType.DAMAGE,
        } and not ((self.reason or "").strip() or (self.notes or "").strip()):
            raise ValueError("reason or notes is required for this movement type")
        return self


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    warehouse_id: UUID
    warehouse_name: str
    item_id: UUID
    item_name: str
    item_type: InventoryItemType
    stock_balance_id: UUID | None = None
    movement_type: StockMovementType
    quantity: Decimal
    previous_quantity_on_hand: Decimal | None = None
    new_quantity_on_hand: Decimal | None = None
    previous_quantity_reserved: Decimal | None = None
    new_quantity_reserved: Decimal | None = None
    previous_quantity_damaged: Decimal | None = None
    new_quantity_damaged: Decimal | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None
    reason: str | None = None
    notes: str | None = None
    created_by: UUID | None = None
    created_by_name: str | None = None
    created_at: datetime


class StockMovementListResponse(BaseModel):
    items: list[StockMovementRead]
    total: int
    page: int
    limit: int
