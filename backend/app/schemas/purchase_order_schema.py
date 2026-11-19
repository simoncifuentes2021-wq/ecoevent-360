from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class PurchaseOrderItemInput(BaseModel):
    description: str = Field(min_length=1, max_length=240)
    unit: str = Field(default="unidad", min_length=1, max_length=40)
    quantity: Decimal = Field(gt=0, le=100000000)
    unit_price: Decimal = Field(ge=0, le=100000000000)
    tax_rate: Decimal = Field(default=Decimal("19"), ge=0, le=100)


class PurchaseOrderCreate(BaseModel):
    event_id: UUID | None = None
    purpose: str = Field(min_length=3, max_length=4000)
    supplier_name: str = Field(min_length=2, max_length=180)
    supplier_rut: str | None = Field(default=None, max_length=30)
    supplier_email: EmailStr | None = None
    supplier_phone: str | None = Field(default=None, max_length=50)
    supplier_address: str | None = Field(default=None, max_length=1000)
    delivery_address: str | None = Field(default=None, max_length=1000)
    issue_date: date
    required_date: date | None = None
    payment_terms: str | None = Field(default=None, max_length=240)
    notes: str | None = Field(default=None, max_length=4000)
    currency: Literal["CLP", "USD", "EUR"] = "CLP"
    items: list[PurchaseOrderItemInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.required_date and self.required_date < self.issue_date:
            raise ValueError("La fecha requerida no puede ser anterior a la emisión")
        return self


class PurchaseOrderUpdate(PurchaseOrderCreate):
    pass


class PurchaseOrderReceiveItem(BaseModel):
    item_id: UUID
    received_quantity: Decimal = Field(gt=0, le=100000000)


class PurchaseOrderReceive(BaseModel):
    items: list[PurchaseOrderReceiveItem] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)


class PurchaseOrderCancel(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class PurchaseOrderItemRead(BaseModel):
    id: UUID
    line_number: int
    description: str
    unit: str
    quantity: Decimal
    received_quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class PurchaseOrderRead(BaseModel):
    id: UUID
    order_number: str
    version: int
    status: str
    event_id: UUID | None
    event_name_snapshot: str | None
    purpose: str
    supplier_name: str
    supplier_rut: str | None
    supplier_email: str | None
    supplier_phone: str | None
    supplier_address: str | None
    delivery_address: str | None
    issue_date: date
    required_date: date | None
    payment_terms: str | None
    notes: str | None
    currency: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    created_by: UUID | None
    approved_by: UUID | None
    sent_by: UUID | None
    approved_at: datetime | None
    sent_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseOrderItemRead]


class PurchaseOrderListRead(BaseModel):
    items: list[PurchaseOrderRead]
    total: int
    page: int
    limit: int
