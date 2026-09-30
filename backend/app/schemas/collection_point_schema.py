from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CollectionPointCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    zone_id: UUID | None = None
    description: str | None = None
    location_description: str | None = None
    capacity_kg: Decimal | None = Field(default=None, ge=0)
    allowed_waste_type_ids: list[UUID] = Field(default_factory=list)


class CollectionPointUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=40)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    zone_id: UUID | None = None
    description: str | None = None
    location_description: str | None = None
    capacity_kg: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None
    allowed_waste_type_ids: list[UUID] | None = None


class CollectionPointWasteTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    is_recyclable: bool | None = None


class CollectionPointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    zone_id: UUID | None
    code: str
    name: str
    description: str | None
    location_description: str | None
    capacity_kg: Decimal | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    record_count: int = 0
    total_kg: Decimal = Decimal("0")
    public_url: str | None = None
    qr_data_url: str | None = None
    allowed_waste_types: list[CollectionPointWasteTypeRead] = Field(default_factory=list)


class PublicWasteRecordCreate(BaseModel):
    client_generated_id: UUID
    device_id: UUID | None = None
    waste_type_id: UUID
    collection_point_id: UUID
    weight_kg: Decimal = Field(gt=0, le=100000)
    submitter_name: str = Field(min_length=2, max_length=160)
    submitter_rut: str = Field(min_length=8, max_length=20)
    recorded_at: datetime

    @field_validator("submitter_rut")
    @classmethod
    def validate_chilean_rut(cls, value: str) -> str:
        normalized = value.replace(".", "").replace("-", "").replace(" ", "").upper()
        if len(normalized) < 2 or not normalized[:-1].isdigit():
            raise ValueError("RUT no válido")
        total = sum(int(digit) * (index % 6 + 2) for index, digit in enumerate(reversed(normalized[:-1])))
        remainder = 11 - total % 11
        verifier = "0" if remainder == 11 else "K" if remainder == 10 else str(remainder)
        if normalized[-1] != verifier:
            raise ValueError("RUT no válido")
        return f"{normalized[:-1]}-{normalized[-1]}"


class PublicCollectionPointRead(BaseModel):
    form_status: str = "ACTIVE"
    event_id: UUID
    event_name: str
    collection_points: list[dict[str, object]]


class EventWastePublicFormRead(BaseModel):
    event_id: UUID
    token: str
    status: str
    public_url: str | None = None
    qr_data_url: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None


class PublicWasteCollectionRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_generated_id: UUID
    waste_type_id: UUID
    weight_kg: Decimal
    submitter_name: str
    recorded_at: datetime
    synced_at: datetime


class WasteCollectionRecordRead(BaseModel):
    id: UUID
    event_id: UUID
    collection_point_id: UUID
    collection_point_code: str
    collection_point_name: str
    waste_type_id: UUID
    waste_type_name: str
    weight_kg: Decimal
    submitter_name: str
    submitter_rut_masked: str
    client_generated_id: UUID
    device_id: UUID | None
    recorded_at: datetime
    synced_at: datetime | None


class WasteCollectionSummaryRead(BaseModel):
    event_id: UUID
    total_kg: Decimal
    records_count: int
    active_points: int
    unique_submitters: int
    by_type: list[dict[str, str | UUID | Decimal | int]]
    by_point: list[dict[str, str | UUID | Decimal | int]]


class PublicWasteBatchRequest(BaseModel):
    items: list[PublicWasteRecordCreate] = Field(min_length=1, max_length=100)


class PublicWasteBatchResponse(BaseModel):
    synced: list[PublicWasteCollectionRecordRead]
    rejected: list[dict[str, str]]
