from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IncidentStatus, PriorityLevel

IncidentType = Literal["SANITARY", "WASTE", "CLEANING", "ENVIRONMENTAL", "SAFETY", "OTHER"]


class IncidentCreate(BaseModel):
    zone_id: UUID | None = None
    assigned_to: UUID | None = None
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    incident_type: IncidentType = "OTHER"
    priority: PriorityLevel = PriorityLevel.MEDIUM


class IncidentUpdate(BaseModel):
    zone_id: UUID | None = None
    assigned_to: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    incident_type: IncidentType | None = None
    status: IncidentStatus | None = None
    priority: PriorityLevel | None = None


class IncidentResolve(BaseModel):
    resolved_at: datetime | None = None


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    zone_id: UUID | None = None
    reported_by: UUID | None = None
    assigned_to: UUID | None = None
    title: str
    description: str | None = None
    incident_type: str | None = None
    status: IncidentStatus
    priority: PriorityLevel
    source: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class IncidentListResponse(BaseModel):
    items: list[IncidentRead]
    total: int
    page: int
    limit: int
