from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    task_id: UUID | None = None
    incident_id: UUID | None = None
    uploaded_by: UUID | None = None
    file_url: str
    file_type: str | None = None
    description: str | None = None
    taken_at: datetime | None = None
    created_at: datetime


class EvidenceListResponse(BaseModel):
    items: list[EvidenceRead]
    total: int
    page: int
    limit: int
