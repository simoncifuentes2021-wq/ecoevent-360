from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import UserRole


class EventStaffCreate(BaseModel):
    user_id: UUID
    role_in_event: str | None = Field(default=None, max_length=100)
    shift_start: datetime | None = None
    shift_end: datetime | None = None

    @model_validator(mode="after")
    def validate_shift(self) -> "EventStaffCreate":
        if self.shift_start and self.shift_end and self.shift_start >= self.shift_end:
            raise ValueError("shift_start must be before shift_end")
        return self


class EventStaffUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone: str | None = None
    role: UserRole
    is_active: bool


class EventStaffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    user_id: UUID
    role_in_event: str | None = None
    shift_start: datetime | None = None
    shift_end: datetime | None = None
    created_at: datetime
    user: EventStaffUserRead | None = None


class EventStaffListResponse(BaseModel):
    items: list[EventStaffRead]
    total: int
