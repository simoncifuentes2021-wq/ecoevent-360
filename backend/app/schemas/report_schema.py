from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.enums import (
    ReportLayoutVariant,
    ReportCompositionMode,
    ReportElementType,
    ReportPublicationStatus,
    ReportScope,
    ReportSectionType,
    ReportStatus,
    ReportTemplateKey,
)
from app.schemas.event_schema import EventRead

Scalar = str | int | float | bool | None
SafeText = Annotated[str, StringConstraints(max_length=10000)]


class ReportField(BaseModel):
    key: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{1,80}$")]
    label: Annotated[str, StringConstraints(min_length=1, max_length=180)]
    auto_value: Scalar = None
    value: Scalar = None
    unit: str | None = Field(default=None, max_length=30)
    description: str | None = Field(default=None, max_length=500)
    is_overridden: bool = False
    source: str = Field(default="MANUAL", max_length=60)
    is_visible: bool = True


class ReportSectionContent(BaseModel):
    text: SafeText | None = None
    text_origin: Literal["MANUAL", "AUTOFILLED", "GENERATED", "ENRICHED"] | None = None
    ai_generation_id: UUID | None = None
    show_traceability: bool = True
    fields: list[ReportField] = Field(default_factory=list, max_length=100)
    items: list[dict[str, Scalar]] = Field(default_factory=list, max_length=500)


class CustomTextContent(BaseModel):
    kind: Literal["TEXT"]
    text: SafeText


class CustomIndicatorContent(BaseModel):
    kind: Literal["INDICATOR"]
    label: str = Field(min_length=1, max_length=180)
    value: Scalar
    unit: str | None = Field(default=None, max_length=30)
    description: str | None = Field(default=None, max_length=500)


class CustomHighlightContent(BaseModel):
    kind: Literal["HIGHLIGHT"]
    text: SafeText


CustomContent = Annotated[
    CustomTextContent | CustomIndicatorContent | CustomHighlightContent, Field(discriminator="kind")
]


class DraftCreate(BaseModel):
    scope: ReportScope
    session_id: UUID | None = None

    @model_validator(mode="after")
    def validate_scope(self):
        if (self.scope == ReportScope.EVENT) != (self.session_id is None):
            raise ValueError("EVENT requires no session_id and SHOW requires session_id")
        return self


Color = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]


class ReportTheme(BaseModel):
    primary_color: Color = "#12372A"
    secondary_color: Color = "#2D6A4F"
    accent_color: Color = "#95D5B2"
    background_color: Color = "#F4F7F5"
    text_color: Color = "#15231D"
    muted_color: Color = "#61736A"
    cover_style: Literal["DARK_OVERLAY", "COLOR_BLOCK", "MINIMAL"] = "DARK_OVERLAY"
    header_style: Literal["MINIMAL", "BRANDED"] = "MINIMAL"
    footer_style: Literal["PAGE_NUMBER", "EVENT_AND_PAGE", "NONE"] = "PAGE_NUMBER"
    show_page_numbers: bool = True
    show_event_name_in_footer: bool = True


class SectionPageOverride(BaseModel):
    mode: Literal["AUTO", "KEEP_WITH_NEXT", "OWN_PAGE", "GROUP_WITH", "NEW_PAGE"] = "AUTO"
    group_with: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,100}$")] | None = None

    @model_validator(mode="after")
    def validate_group(self):
        if (self.mode == "GROUP_WITH") != (self.group_with is not None):
            raise ValueError("GROUP_WITH requires group_with")
        return self


ReportVisualPreset = Literal[
    "AUTO", "ECOEVENT_EDITORIAL", "EXECUTIVE", "ENVIRONMENTAL", "BIKE_ZONE", "IMPACT"
]
ReportVisualVariant = Literal[
    "AUTO", "IMPACT_STORY", "SHOW_COMPARISON", "CARD_GRID", "SECTION_HERO", "PHOTO_STORY"
]


class ReportVisualConfig(BaseModel):
    preset: ReportVisualPreset = "AUTO"
    icon_density: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    visual_density: Literal["AIRY", "BALANCED", "COMPACT"] = "BALANCED"
    show_icons: bool = True
    show_trends: bool = True
    show_equivalences: bool = True


class ReportSectionVisualConfig(BaseModel):
    variant: ReportVisualVariant = "AUTO"
    icon_key: Literal[
        "LEAF", "RECYCLE", "BICYCLE", "CARBON", "ENERGY", "WATER", "PEOPLE",
        "LOCATION", "CALENDAR", "CHART", "CHECK", "ALERT", "LIGHTBULB", "CAMERA", "TARGET",
    ] | None = None
    show_icon: bool = True
    show_trend: bool = True
    premium_variant: Annotated[str, StringConstraints(pattern=r"^[A-Z0-9_]{1,100}$")] = "AUTO"
    emphasis: Literal["LOW", "NORMAL", "HIGH"] = "NORMAL"
    selected_metric_keys: list[
        Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_.:-]{1,180}$")]
    ] = Field(default_factory=list, max_length=30)


class ReportEditorialConfig(BaseModel):
    mode: Literal["AUTO", "CUSTOM"] = "AUTO"
    cover_style: Literal["FULL_PHOTO", "SIDE_PHOTO", "EDITORIAL", "MINIMAL_PREMIUM"] = "FULL_PHOTO"
    cover_evidence_id: UUID | None = None
    cover_show_photo: bool = True
    target_page_count: int | None = Field(default=None, ge=1, le=50)
    featured_kpi_ids: list[Annotated[str, StringConstraints(pattern=r"^[a-z0-9_.-]{1,100}$")]] = (
        Field(default_factory=list, max_length=6)
    )
    page_overrides: dict[
        Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,100}$")], SectionPageOverride
    ] = Field(default_factory=dict)
    chart_types: dict[
        Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,100}$")],
        Literal["BAR", "DONUT", "COMPARISON", "DISTRIBUTION"],
    ] = Field(default_factory=dict)
    visual_config: ReportVisualConfig = Field(default_factory=ReportVisualConfig)
    section_visuals: dict[
        Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,100}$")],
        ReportSectionVisualConfig,
    ] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_kpis(self):
        if self.featured_kpi_ids and len(self.featured_kpi_ids) < 3:
            raise ValueError("Select either zero or 3 to 6 featured KPIs")
        if len(set(self.featured_kpi_ids)) != len(self.featured_kpi_ids):
            raise ValueError("Featured KPIs must be unique")
        return self


class ReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    summary: SafeText | None = None
    edit_version: int = Field(ge=1)
    template_key: ReportTemplateKey | None = None
    theme: ReportTheme | None = None
    editorial_config: ReportEditorialConfig | None = None


class SectionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    is_enabled: bool | None = None
    layout_variant: ReportLayoutVariant | None = None
    content: ReportSectionContent | None = None
    edit_version: int = Field(ge=1)


class CustomSectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    content: CustomContent
    edit_version: int = Field(ge=1)


class SectionOrderUpdate(BaseModel):
    section_ids: list[UUID] = Field(min_length=1, max_length=50)
    edit_version: int = Field(ge=1)


class EvidenceAdd(BaseModel):
    evidence_id: UUID
    section_id: UUID | None = None
    caption: str | None = Field(default=None, max_length=500)
    edit_version: int = Field(ge=1)


class EvidenceUpdate(BaseModel):
    section_id: UUID | None = None
    caption: str | None = Field(default=None, max_length=500)
    is_enabled: bool | None = None
    edit_version: int = Field(ge=1)


class RevisionCreate(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    edit_version: int = Field(ge=1)


class RestoreRevision(BaseModel):
    edit_version: int = Field(ge=1)


class ReportSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    report_id: UUID
    section_key: str
    section_type: ReportSectionType
    title: str
    layout_variant: ReportLayoutVariant
    is_enabled: bool
    sort_order: int
    content: dict
    source_snapshot: dict
    source_metadata: dict
    is_custom: bool
    edit_version: int
    created_at: datetime
    updated_at: datetime


class ReportEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    report_id: UUID
    section_id: UUID | None
    evidence_id: UUID
    sort_order: int
    caption: str | None
    is_enabled: bool
    created_at: datetime


class ReportRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    report_id: UUID
    revision_number: int
    snapshot: dict
    created_by: UUID | None
    note: str | None
    created_at: datetime


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    event: EventRead | None = None
    title: str
    summary: str | None = None
    pdf_url: str | None = None
    status: ReportStatus
    scope: ReportScope = ReportScope.EVENT
    session_id: UUID | None = None
    generated_by: UUID | None = None
    generated_at: datetime | None = None
    delivered_at: datetime | None = None
    created_by: UUID | None = None
    edit_version: int = 1
    created_at: datetime
    updated_at: datetime | None = None
    template_key: ReportTemplateKey = ReportTemplateKey.ENVIRONMENTAL_PREMIUM
    theme: dict = Field(default_factory=dict)
    editorial_config: dict = Field(default_factory=dict)
    composition_mode: ReportCompositionMode = ReportCompositionMode.AUTO


class ReportLayoutOverrideBase(BaseModel):
    element_key: str = Field(min_length=3, max_length=220, pattern=r"^[a-z0-9][a-z0-9_.:-]*$")
    page_key: str | None = Field(default=None, max_length=160, pattern=r"^[a-z0-9][a-z0-9_.:-]*$")
    x_offset: float = Field(default=0, ge=-2000, le=2000)
    y_offset: float = Field(default=0, ge=-3000, le=3000)
    width_scale: float = Field(default=1, ge=0.1, le=5)
    height_scale: float = Field(default=1, ge=0.1, le=5)
    box_width: float | None = Field(default=None, ge=24, le=2000)
    box_height: float | None = Field(default=None, ge=16, le=3000)
    rotation: float = Field(default=0, ge=-360, le=360)
    z_index: int = Field(default=0, ge=-10000, le=10000)
    locked: bool = False
    visible: bool = True


class ReportLayoutOverrideUpsert(ReportLayoutOverrideBase):
    pass


class ReportLayoutOverrideBatch(BaseModel):
    overrides: list[ReportLayoutOverrideUpsert] = Field(min_length=1, max_length=100)


class ReportLayoutOverrideRead(ReportLayoutOverrideBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    report_id: UUID
    created_at: datetime
    updated_at: datetime


class ReportPageCreate(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    width: float = Field(default=1000, gt=0, le=5000)
    height: float = Field(default=1414, gt=0, le=7000)
    background: Color = "#FFFFFF"
    background_image: str | None = Field(default=None, max_length=2000)
    is_enabled: bool = True


class ReportPageUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    page_number: int | None = Field(default=None, ge=1)
    width: float | None = Field(default=None, gt=0, le=5000)
    height: float | None = Field(default=None, gt=0, le=7000)
    background: Color | None = None
    background_image: str | None = Field(default=None, max_length=2000)
    is_enabled: bool | None = None


class ReportElementBase(BaseModel):
    type: ReportElementType
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation: float = Field(default=0, ge=-360, le=360)
    z_index: int = Field(default=0, ge=-10000, le=10000)
    locked: bool = False
    visible: bool = True
    content: dict = Field(default_factory=dict)
    style: dict = Field(default_factory=dict)
    data_binding: dict | None = None
    metadata: dict = Field(default_factory=dict)


class ReportElementCreate(ReportElementBase):
    pass


class ReportElementUpdate(BaseModel):
    type: ReportElementType | None = None
    x: float | None = Field(default=None, ge=0)
    y: float | None = Field(default=None, ge=0)
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    rotation: float | None = Field(default=None, ge=-360, le=360)
    z_index: int | None = Field(default=None, ge=-10000, le=10000)
    locked: bool | None = None
    visible: bool | None = None
    content: dict | None = None
    style: dict | None = None
    data_binding: dict | None = None
    metadata: dict | None = None


class ReportElementBatchItem(ReportElementUpdate):
    id: UUID


class ReportElementBatchUpdate(BaseModel):
    elements: list[ReportElementBatchItem] = Field(min_length=1, max_length=200)


class ReportElementRead(ReportElementBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    page_id: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, element):
        values = {
            column: getattr(element, column)
            for column in (
                "id",
                "page_id",
                "type",
                "x",
                "y",
                "width",
                "height",
                "rotation",
                "z_index",
                "locked",
                "visible",
                "content",
                "style",
                "data_binding",
                "created_at",
                "updated_at",
            )
        }
        values["metadata"] = element.metadata_
        return cls.model_validate(values)


class ReportPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    report_id: UUID
    page_number: int
    name: str | None
    width: float
    height: float
    background: str
    background_image: str | None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime
    elements: list[ReportElementRead] = Field(default_factory=list)

    @classmethod
    def from_model(cls, page):
        values = {
            column: getattr(page, column)
            for column in (
                "id",
                "report_id",
                "page_number",
                "name",
                "width",
                "height",
                "background",
                "background_image",
                "is_enabled",
                "created_at",
                "updated_at",
            )
        }
        values["elements"] = [ReportElementRead.from_model(element) for element in page.elements]
        return cls.model_validate(values)


class ReportTemplateLayoutCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=500)


class ReportTemplateLayoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    pages: list[dict]
    is_system: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class ReportPagePlanItem(BaseModel):
    number: int
    recipe: str
    density: Literal["LOW", "MEDIUM", "HIGH"]
    title: str
    section_keys: list[str]


class ReportPagePlanRead(BaseModel):
    mode: Literal["AUTO", "CUSTOM"]
    pages: list[ReportPagePlanItem]


class ReportEditor(ReportRead):
    sections: list[ReportSectionRead]
    evidences: list[ReportEvidenceRead]


class ReportAIEditorialApplyResponse(BaseModel):
    revision_id: UUID
    report: ReportEditor
    visual_audit: dict | None = None


class AvailableEvidence(BaseModel):
    id: UUID
    file_type: str | None
    description: str | None
    taken_at: datetime | None
    session_id: UUID | None
    preview_url: str
    selected: bool


class ReportListResponse(BaseModel):
    items: list[ReportRead]
    total: int
    page: int
    limit: int


class PublicationGenerate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class ReportPublicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    report_id: UUID
    revision_id: UUID | None
    publication_number: int
    status: ReportPublicationStatus
    sha256: str
    file_size: int
    page_count: int
    generated_by: UUID | None
    generated_at: datetime
    delivered_by: UUID | None
    delivered_at: datetime | None
    created_at: datetime
