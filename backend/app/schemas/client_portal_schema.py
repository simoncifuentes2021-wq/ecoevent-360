from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ClientPortalSectionUpdate(BaseModel):
    section_key: str = Field(max_length=100)
    label: str | None = Field(default=None, max_length=160)
    is_enabled: bool = True
    sort_order: int = 0


class ClientPortalWidgetUpdate(BaseModel):
    widget_key: str = Field(max_length=120)
    section_key: str = Field(max_length=100)
    label: str | None = Field(default=None, max_length=180)
    is_enabled: bool = True
    sort_order: int = 0
    visibility_config: dict = Field(default_factory=dict)


class ClientPortalConfigUpdate(BaseModel):
    scope: str = Field(default="EVENT", max_length=30)
    is_active: bool = True
    sections: list[ClientPortalSectionUpdate] = Field(default_factory=list)
    widgets: list[ClientPortalWidgetUpdate] = Field(default_factory=list)


class ClientPortalTemplateApply(BaseModel):
    template_key: str = Field(max_length=60)


class ClientPortalSectionRead(ORMModel):
    id: UUID | None = None
    section_key: str
    label: str
    is_enabled: bool
    sort_order: int


class ClientPortalWidgetRead(ORMModel):
    id: UUID | None = None
    widget_key: str
    section_key: str
    label: str
    is_enabled: bool
    sort_order: int
    visibility_config: dict = Field(default_factory=dict)


class ClientPortalConfigRead(ORMModel):
    id: UUID
    client_id: UUID
    event_id: UUID
    scope: str
    is_active: bool
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    sections: list[ClientPortalSectionRead]
    widgets: list[ClientPortalWidgetRead]


class ClientPortalVisibleSection(BaseModel):
    section_key: str
    label: str
    sort_order: int


class ClientPortalVisibleWidget(BaseModel):
    widget_key: str
    section_key: str
    label: str
    sort_order: int
    value: str | int | float | bool | None = None
    data: dict | list | None = None
    visibility_config: dict = {}


class ClientPortalResponse(BaseModel):
    event_id: UUID
    client_id: UUID
    config_id: UUID
    sections: list[ClientPortalVisibleSection]
    widgets: list[ClientPortalVisibleWidget]
    data: dict = Field(default_factory=dict)
