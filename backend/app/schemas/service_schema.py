from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str | None = Field(default=None, max_length=120)
    description: str | None = None
    unit: str | None = Field(default=None, max_length=50)
    base_price: Decimal | None = Field(default=None, ge=0)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, max_length=120)
    description: str | None = None
    unit: str | None = Field(default=None, max_length=50)
    base_price: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str | None = None
    description: str | None = None
    unit: str | None = None
    base_price: Decimal | None = None
    is_active: bool
    created_at: datetime


class ServiceListResponse(BaseModel):
    items: list[ServiceRead]
    total: int
    page: int
    limit: int
