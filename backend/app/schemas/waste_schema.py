from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import WasteDestination


class WasteTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    is_recyclable: bool | None = False


class WasteTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    is_recyclable: bool | None = None


class WasteTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    is_recyclable: bool | None = None
    created_at: datetime


class WasteTypeListResponse(BaseModel):
    items: list[WasteTypeRead]
    total: int
    page: int
    limit: int


class WasteRecordCreate(BaseModel):
    zone_id: UUID | None = None
    waste_type_id: UUID
    weight_kg: Decimal = Field(ge=0)
    destination: WasteDestination
    destination_detail: str | None = None
    evidence_id: UUID | None = None
    recorded_at: datetime | None = None


class WasteRecordUpdate(BaseModel):
    zone_id: UUID | None = None
    waste_type_id: UUID | None = None
    weight_kg: Decimal | None = Field(default=None, ge=0)
    destination: WasteDestination | None = None
    destination_detail: str | None = None
    evidence_id: UUID | None = None
    recorded_at: datetime | None = None


class WasteRecordUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str


class WasteRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    zone_id: UUID | None = None
    waste_type_id: UUID | None = None
    weight_kg: Decimal
    destination: WasteDestination
    destination_detail: str | None = None
    recorded_by: UUID | None = None
    evidence_id: UUID | None = None
    recorded_at: datetime
    created_at: datetime
    recorder: WasteRecordUserRead | None = None


class WasteRecordListResponse(BaseModel):
    items: list[WasteRecordRead]
    total: int
    page: int
    limit: int


class WasteSummaryGroup(BaseModel):
    id: UUID | None = None
    name: str
    total_kg: Decimal


class WasteSummaryRead(BaseModel):
    event_id: UUID
    total_kg: Decimal
    recovered_kg: Decimal
    landfill_kg: Decimal
    special_disposal_kg: Decimal
    recovery_percentage: Decimal
    by_type: list[WasteSummaryGroup]
    by_destination: list[WasteSummaryGroup]
    by_zone: list[WasteSummaryGroup]
