from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import LogisticsEvidenceStage


class LogisticsEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID | None = None
    logistics_order_id: UUID | None = None
    logistics_order_item_id: UUID | None = None
    purchase_request_id: UUID | None = None
    purchase_request_item_id: UUID | None = None
    stock_movement_id: UUID | None = None
    warehouse_id: UUID | None = None
    evidence_stage: LogisticsEvidenceStage
    file_url: str
    file_key: str | None = None
    file_name: str | None = None
    file_type: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    notes: str | None = None
    uploaded_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class LogisticsEvidenceListResponse(BaseModel):
    items: list[LogisticsEvidenceRead]
    total: int
    page: int
    limit: int
