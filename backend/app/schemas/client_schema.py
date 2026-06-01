from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import EventStatus


class ClientCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=180)
    rut: str | None = Field(default=None, max_length=30)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    industry: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class ClientUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=1, max_length=180)
    rut: str | None = Field(default=None, max_length=30)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    industry: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    is_active: bool | None = None


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_name: str
    rut: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    address: str | None = None
    industry: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClientListResponse(BaseModel):
    items: list[ClientRead]
    total: int
    page: int
    limit: int


class ClientEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    event_type: str | None = None
    start_date: datetime
    end_date: datetime
    status: EventStatus
    estimated_attendees: int | None = None


class ClientEventListResponse(BaseModel):
    items: list[ClientEventRead]
    total: int
    page: int
    limit: int

