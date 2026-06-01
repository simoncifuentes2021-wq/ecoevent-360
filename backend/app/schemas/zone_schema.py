from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    qr_code_url: str | None = None


class EventZoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    qr_code_url: str | None = None


class EventZoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    name: str
    description: str | None = None
    qr_code_url: str | None = None
    created_at: datetime
