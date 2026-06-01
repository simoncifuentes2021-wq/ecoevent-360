from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CarbonScope


class CarbonFactorCreate(BaseModel):
    category: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=180)
    unit: str = Field(min_length=1, max_length=50)
    factor_kgco2e: Decimal = Field(ge=0)
    scope: CarbonScope | None = None
    source: str | None = None
    year: int | None = None
    country: str | None = Field(default=None, max_length=100)


class CarbonFactorUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    factor_kgco2e: Decimal | None = Field(default=None, ge=0)
    scope: CarbonScope | None = None
    source: str | None = None
    year: int | None = None
    country: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class CarbonFactorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    name: str
    unit: str
    factor_kgco2e: Decimal
    scope: CarbonScope | None = None
    source: str | None = None
    year: int | None = None
    country: str | None = None
    is_active: bool
    created_at: datetime


class CarbonFactorListResponse(BaseModel):
    items: list[CarbonFactorRead]
    total: int
    page: int
    limit: int


class CarbonRecordCreate(BaseModel):
    factor_id: UUID
    description: str | None = None
    activity_value: Decimal = Field(ge=0)
    activity_unit: str = Field(min_length=1, max_length=50)


class CarbonRecordUpdate(BaseModel):
    factor_id: UUID | None = None
    description: str | None = None
    activity_value: Decimal | None = Field(default=None, ge=0)
    activity_unit: str | None = Field(default=None, min_length=1, max_length=50)


class CarbonRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    factor_id: UUID
    category: str
    description: str | None = None
    activity_value: Decimal
    activity_unit: str
    emissions_kgco2e: Decimal
    recorded_by: UUID | None = None
    created_at: datetime


class CarbonRecordListResponse(BaseModel):
    items: list[CarbonRecordRead]
    total: int
    page: int
    limit: int


class CarbonSummaryGroup(BaseModel):
    id: UUID | None = None
    name: str
    total_kgco2e: Decimal


class CarbonSummaryRead(BaseModel):
    event_id: UUID
    total_kgco2e: Decimal
    total_tco2e: Decimal
    kgco2e_per_attendee: Decimal | None = None
    by_category: list[CarbonSummaryGroup]
    by_scope: list[CarbonSummaryGroup]
    by_factor: list[CarbonSummaryGroup]


class FuelRecordCreate(BaseModel):
    vehicle_name: str | None = Field(default=None, max_length=160)
    vehicle_plate: str | None = Field(default=None, max_length=40)
    fuel_type: str | None = Field(default=None, max_length=80)
    liters: Decimal | None = Field(default=None, ge=0)
    kilometers: Decimal | None = Field(default=None, ge=0)
    trips: int | None = Field(default=1, ge=0)


class FuelRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    vehicle_name: str | None = None
    vehicle_plate: str | None = None
    fuel_type: str | None = None
    liters: Decimal | None = None
    kilometers: Decimal | None = None
    trips: int | None = None
    recorded_by: UUID | None = None
    created_at: datetime


class EnergyRecordCreate(BaseModel):
    source: str | None = Field(default=None, max_length=100)
    kwh: Decimal | None = Field(default=None, ge=0)
    hours_used: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None


class EnergyRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    source: str | None = None
    kwh: Decimal | None = None
    hours_used: Decimal | None = None
    notes: str | None = None
    recorded_by: UUID | None = None
    created_at: datetime


class WaterRecordCreate(BaseModel):
    source: str | None = Field(default=None, max_length=100)
    liters: Decimal = Field(ge=0)
    usage_type: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class WaterRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    source: str | None = None
    liters: Decimal
    usage_type: str | None = None
    notes: str | None = None
    recorded_by: UUID | None = None
    created_at: datetime
