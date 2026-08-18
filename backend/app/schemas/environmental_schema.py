from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.models.enums import (
    EnvironmentalActionStatus,
    EnvironmentalActionType,
    EnvironmentalEnergySource,
    EnvironmentalMetricKey,
)


class EnvironmentalActionCreate(BaseModel):
    session_id: UUID | None = None
    methodology_id: UUID | None = None
    action_type: EnvironmentalActionType
    name: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=4000)
    quantity_used: Decimal = Field(gt=0)
    hours_used: Decimal | None = Field(default=None, ge=0)
    distance_km: Decimal | None = Field(default=None, ge=0)
    energy_kwh: Decimal | None = Field(default=None, ge=0)
    power_kw: Decimal | None = Field(default=None, ge=0)
    energy_source: EnvironmentalEnergySource | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("quantity_used", "hours_used", "distance_km", "energy_kwh", "power_kw")
    @classmethod
    def finite(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("Value must be finite")
        return value

    @model_validator(mode="after")
    def energy_provenance(self):
        if self.energy_kwh is not None and self.energy_source is None:
            raise ValueError("energy_source is required when energy_kwh is provided")
        return self


class EnvironmentalActionUpdate(BaseModel):
    session_id: UUID | None = None
    methodology_id: UUID | None = None
    action_type: EnvironmentalActionType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=4000)
    quantity_used: Decimal | None = Field(default=None, gt=0)
    hours_used: Decimal | None = Field(default=None, ge=0)
    distance_km: Decimal | None = Field(default=None, ge=0)
    energy_kwh: Decimal | None = Field(default=None, ge=0)
    power_kw: Decimal | None = Field(default=None, ge=0)
    energy_source: EnvironmentalEnergySource | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("quantity_used", "hours_used", "distance_km", "energy_kwh", "power_kw")
    @classmethod
    def finite(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("Value must be finite")
        return value


class EnvironmentalMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    metric_key: EnvironmentalMetricKey
    unit: str
    calculated_value: Decimal | None
    reported_value: Decimal | None
    value: Decimal | None
    is_manual_override: bool
    override_reason: str | None
    calculation_method: str
    calculated_at: datetime


class EnvironmentalActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    session_id: UUID | None
    methodology_id: UUID | None
    action_type: EnvironmentalActionType
    status: EnvironmentalActionStatus
    name: str
    description: str | None
    quantity_used: Decimal
    hours_used: Decimal | None
    distance_km: Decimal | None
    energy_kwh: Decimal | None
    power_kw: Decimal | None
    energy_source: EnvironmentalEnergySource | None
    notes: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    metrics: list[EnvironmentalMetricRead] = []


class EnvironmentalActionList(BaseModel):
    items: list[EnvironmentalActionRead]
    total: int


class EnvironmentalFactorBase(BaseModel):
    impact_type: str = Field(min_length=1, max_length=30)
    technology: str = Field(min_length=1, max_length=120)
    pollutant: str | None = Field(default=None, max_length=30)
    unit_basis: str = Field(min_length=1, max_length=50)
    factor_value: Decimal = Field(ge=0)
    factor_unit: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=2000)
    source_url: HttpUrl | None = None
    year: int = Field(ge=1900, le=2200)
    country: str | None = Field(default=None, max_length=100)
    methodology: str = Field(min_length=1, max_length=4000)


class EnvironmentalFactorCreate(EnvironmentalFactorBase):
    pass


class EnvironmentalFactorUpdate(BaseModel):
    factor_value: Decimal | None = Field(default=None, ge=0)
    source: str | None = Field(default=None, min_length=1, max_length=2000)
    methodology: str | None = Field(default=None, min_length=1, max_length=4000)
    is_active: bool | None = None


class EnvironmentalFactorRead(EnvironmentalFactorBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EnvironmentalMethodologyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    action_type: EnvironmentalActionType
    baseline_technology: str = Field(min_length=1, max_length=180)
    actual_technology: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=4000)
    parameters: dict = Field(default_factory=dict)


class EnvironmentalMethodologyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    parameters: dict | None = None
    is_active: bool | None = None


class EnvironmentalMethodologyRead(EnvironmentalMethodologyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EcoEquivalenceCreate(BaseModel):
    key: str = Field(pattern=r"^[A-Z0-9_]+$", min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    metric_source: EnvironmentalMetricKey
    factor: Decimal = Field(ge=0)
    unit: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=2000)
    year: int = Field(ge=1900, le=2200)


class EcoEquivalenceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    factor: Decimal | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=80)
    source: str | None = Field(default=None, min_length=1, max_length=2000)
    year: int | None = Field(default=None, ge=1900, le=2200)
    is_active: bool | None = None


class EcoEquivalenceRead(EcoEquivalenceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MetricOverride(BaseModel):
    reported_value: Decimal
    override_reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reported_value")
    @classmethod
    def finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Value must be finite")
        return value


class EnvironmentalSummary(BaseModel):
    event_id: UUID
    session_id: UUID | None
    actions_count: int
    energy_kwh: Decimal | None
    fuel_avoided_l: Decimal | None
    co2e_avoided_kg: Decimal | None
    pm25_avoided_kg: Decimal | None
    pm10_avoided_kg: Decimal | None
    nox_avoided_kg: Decimal | None
    unavailable_metrics: list[EnvironmentalMetricKey]
