from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import IncidentStatus, TaskStatus
from app.schemas.staff_schema import EventStaffUserRead


class EventSessionStaffCreate(BaseModel):
    event_staff_id: UUID
    shift_start: datetime | None = None
    shift_end: datetime | None = None
    operational_role: str | None = Field(default=None, max_length=100)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_shift(self):
        if self.shift_start and self.shift_end and self.shift_start >= self.shift_end:
            raise ValueError("shift_start must be before shift_end")
        return self


class EventSessionStaffUpdate(BaseModel):
    shift_start: datetime | None = None
    shift_end: datetime | None = None
    operational_role: str | None = Field(default=None, max_length=100)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_shift(self):
        if self.shift_start and self.shift_end and self.shift_start >= self.shift_end:
            raise ValueError("shift_start must be before shift_end")
        return self


class EventSessionStaffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    session_id: UUID
    event_staff_id: UUID
    shift_start: datetime | None = None
    shift_end: datetime | None = None
    operational_role: str | None = None
    notes: str | None = None
    overlap_warning: bool = False
    user: EventStaffUserRead | None = None
    created_at: datetime
    updated_at: datetime


class EventSessionStaffListResponse(BaseModel):
    items: list[EventSessionStaffRead]
    total: int
    page: int
    limit: int


class ShowOperationalSummary(BaseModel):
    staff_count: int
    active_shift_count: int
    tasks_by_status: dict[TaskStatus, int]
    incidents_by_status: dict[IncidentStatus, int]
    evidence_count: int
