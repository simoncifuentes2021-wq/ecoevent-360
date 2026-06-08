from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ReportStatus
from app.schemas.event_schema import EventRead


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    event: EventRead | None = None
    title: str
    summary: str | None = None
    pdf_url: str | None = None
    status: ReportStatus
    generated_by: UUID | None = None
    generated_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime


class ReportListResponse(BaseModel):
    items: list[ReportRead]
    total: int
    page: int
    limit: int
