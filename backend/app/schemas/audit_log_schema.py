from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AuditLogCreateInternal(BaseModel):
    user_id: UUID | None = None
    event_id: UUID | None = None
    client_id: UUID | None = None
    task_id: UUID | None = None
    incident_id: UUID | None = None
    zone_id: UUID | None = None
    action: str = Field(max_length=120)
    module: str = Field(max_length=120)
    entity_type: str | None = Field(default=None, max_length=120)
    entity_id: UUID | None = None
    status: str = Field(default="SUCCESS", max_length=50)
    old_data: dict | None = None
    new_data: dict | None = None
    metadata: dict | None = None
    description: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_method: str | None = None
    request_path: str | None = None


class AuditLogFilters(BaseModel):
    user_id: UUID | None = None
    event_id: UUID | None = None
    client_id: UUID | None = None
    task_id: UUID | None = None
    incident_id: UUID | None = None
    zone_id: UUID | None = None
    module: str | None = None
    action: str | None = None
    status: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    q: str | None = None


class AuditLogRead(BaseModel):
    id: UUID
    user_id: UUID | None = None
    user_name: str | None = None
    user_email: str | None = None
    user_role: str | None = None
    event_id: UUID | None = None
    event_name: str | None = None
    client_id: UUID | None = None
    client_name: str | None = None
    task_id: UUID | None = None
    task_title: str | None = None
    incident_id: UUID | None = None
    incident_title: str | None = None
    zone_id: UUID | None = None
    zone_name: str | None = None
    action: str
    module: str
    entity_type: str | None = None
    entity_id: UUID | None = None
    status: str
    old_data: dict | None = None
    new_data: dict | None = None
    metadata: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_method: str | None = None
    request_path: str | None = None
    description: str | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    limit: int
    pages: int
