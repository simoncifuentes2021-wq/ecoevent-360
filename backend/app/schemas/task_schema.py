from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PriorityLevel, TaskStatus


class TaskCreate(BaseModel):
    zone_id: UUID | None = None
    assigned_to: UUID | None = None
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    priority: PriorityLevel = PriorityLevel.MEDIUM
    scheduled_at: datetime | None = None


class TaskUpdate(BaseModel):
    zone_id: UUID | None = None
    assigned_to: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    priority: PriorityLevel | None = None
    scheduled_at: datetime | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskComplete(BaseModel):
    completed_at: datetime | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    zone_id: UUID | None = None
    assigned_to: UUID | None = None
    title: str
    description: str | None = None
    status: TaskStatus
    priority: PriorityLevel
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskRead]
    total: int
    page: int
    limit: int
