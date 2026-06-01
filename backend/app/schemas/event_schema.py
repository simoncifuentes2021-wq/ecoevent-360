from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import EventStatus


class EventBase(BaseModel):
    client_id: UUID
    name: str = Field(min_length=1, max_length=180)
    event_type: str | None = Field(default=None, max_length=100)
    description: str | None = None
    location_name: str | None = Field(default=None, max_length=180)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    start_date: datetime
    end_date: datetime
    estimated_attendees: int | None = Field(default=0, ge=0)
    real_attendees: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_dates(self) -> "EventBase":
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class EventCreate(EventBase):
    status: EventStatus | None = None


class EventUpdate(BaseModel):
    client_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    event_type: str | None = Field(default=None, max_length=100)
    description: str | None = None
    location_name: str | None = Field(default=None, max_length=180)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    estimated_attendees: int | None = Field(default=None, ge=0)
    real_attendees: int | None = Field(default=None, ge=0)


class EventStatusUpdate(BaseModel):
    status: EventStatus


class EventClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_name: str
    rut: str | None = None
    contact_email: str | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    name: str
    event_type: str | None = None
    description: str | None = None
    location_name: str | None = None
    address: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    start_date: datetime
    end_date: datetime
    estimated_attendees: int | None = None
    real_attendees: int | None = None
    status: EventStatus
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class EventDetailRead(EventRead):
    client: EventClientRead
    services_count: int
    zones_count: int


class EventListResponse(BaseModel):
    items: list[EventRead]
    total: int
    page: int
    limit: int


class EventServiceCreate(BaseModel):
    service_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None


class EventServiceUpdate(BaseModel):
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None


class EventServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    service_id: UUID
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    notes: str | None = None
    created_at: datetime
