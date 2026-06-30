from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import InventoryItemType


class InventoryItemBase(BaseModel):
    sku: str | None = Field(default=None, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    item_type: InventoryItemType
    return_required: bool | None = None
    unit: str | None = Field(default=None, max_length=50)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    replacement_cost: Decimal | None = Field(default=None, ge=0)
    min_stock: Decimal = Field(default=Decimal("0"), ge=0)

    @field_validator("min_stock")
    @classmethod
    def validate_integer_min_stock(cls, value: Decimal) -> Decimal:
        if value != value.to_integral_value():
            raise ValueError("min_stock must be an integer")
        return value

    @model_validator(mode="after")
    def normalize_return_required(self):
        if self.item_type == InventoryItemType.RETURNABLE:
            self.return_required = True
        elif self.item_type in {InventoryItemType.CONSUMABLE, InventoryItemType.DISPOSABLE}:
            self.return_required = False
        elif self.return_required is None:
            self.return_required = False
        return self


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    item_type: InventoryItemType | None = None
    return_required: bool | None = None
    unit: str | None = Field(default=None, max_length=50)
    unit_price: Decimal | None = Field(default=None, ge=0)
    replacement_cost: Decimal | None = Field(default=None, ge=0)
    min_stock: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("min_stock")
    @classmethod
    def validate_integer_min_stock(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value != value.to_integral_value():
            raise ValueError("min_stock must be an integer")
        return value


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku: str | None = None
    name: str
    description: str | None = None
    item_type: InventoryItemType
    return_required: bool
    unit: str | None = None
    unit_price: Decimal
    replacement_cost: Decimal | None = None
    min_stock: Decimal
    is_active: bool
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class InventoryItemListResponse(BaseModel):
    items: list[InventoryItemRead]
    total: int
    page: int
    limit: int
