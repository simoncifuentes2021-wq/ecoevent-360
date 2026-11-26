from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ChecklistStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED"]


class ChecklistItemCreate(BaseModel):
    user_id: UUID | None = None
    title: str = Field(min_length=1, max_length=180)
    details: str | None = Field(default=None, max_length=4000)
    due_at: datetime


class ChecklistItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    details: str | None = Field(default=None, max_length=4000)
    due_at: datetime | None = None
    status: ChecklistStatus | None = None
    status_note: str | None = Field(default=None, max_length=2000)


class ChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    user_id: UUID
    title: str
    details: str | None
    due_at: datetime
    status: ChecklistStatus
    status_note: str | None
    reminder_sent_at: datetime | None
    reminder_attempts: int
    reminder_failed: bool
    created_by: UUID | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime
    owner_name: str
    owner_email: str


class ChecklistHistoryRead(BaseModel):
    id: UUID
    actor_name: str
    action: str
    description: str
    created_at: datetime


class ChecklistPersonRead(BaseModel):
    id: UUID
    full_name: str
    email: str
