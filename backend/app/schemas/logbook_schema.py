# ruff: noqa: F405
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.enums import *  # noqa: F403


class OptionIn(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=80)
    position: int = Field(ge=0)
    is_success_value: bool = False
    is_failure_value: bool = False


class ItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    instructions: str | None = None
    position: int = Field(ge=0)
    item_type: LogbookItemType
    is_required: bool = True
    allow_not_applicable: bool = False
    evidence_policy: LogbookEvidencePolicy = LogbookEvidencePolicy.NONE
    min_evidences: int = Field(0, ge=0, le=10)
    max_evidences: int = Field(5, ge=0, le=10)
    require_comment_on_failure: bool = False
    requires_supervisor_review: bool = False
    client_visible_by_default: bool = False
    creates_incident_suggestion: bool = False
    options: list[OptionIn] = []

    @model_validator(mode="after")
    def valid(self):
        if self.min_evidences > self.max_evidences:
            raise ValueError("min_evidences cannot exceed max_evidences")
        if self.item_type == LogbookItemType.STATUS_SELECT and not self.options:
            raise ValueError("STATUS_SELECT requires options")
        return self


class SectionIn(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    position: int = Field(ge=0)
    is_required: bool = True
    items: list[ItemIn] = []

    @model_validator(mode="after")
    def unique_item_positions(self):
        positions = [item.position for item in self.items]
        if len(positions) != len(set(positions)):
            raise ValueError("Item positions must be unique within a section")
        return self


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    instructions: str | None = None
    operational_stage: LogbookOperationalStage
    default_assignment_mode: LogbookAssignmentMode
    default_client_visibility: bool = False
    change_notes: str | None = None
    sections: list[SectionIn] = []

    @model_validator(mode="after")
    def unique_section_positions(self):
        positions = [section.position for section in self.sections]
        if len(positions) != len(set(positions)):
            raise ValueError("Section positions must be unique")
        return self


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=180)
    description: str | None = None
    instructions: str | None = None
    operational_stage: LogbookOperationalStage | None = None
    default_assignment_mode: LogbookAssignmentMode | None = None
    default_client_visibility: bool | None = None
    change_notes: str | None = None
    sections: list[SectionIn] | None = None

    @model_validator(mode="after")
    def unique_section_positions(self):
        if self.sections is not None:
            positions = [section.position for section in self.sections]
            if len(positions) != len(set(positions)):
                raise ValueError("Section positions must be unique")
        return self


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    instructions: str | None
    operational_stage: LogbookOperationalStage
    status: LogbookTemplateStatus
    default_assignment_mode: LogbookAssignmentMode
    default_client_visibility: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class TemplateList(BaseModel):
    items: list[TemplateRead]
    total: int
    page: int
    limit: int


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    template_id: UUID
    version_number: int
    status: LogbookVersionStatus
    change_notes: str | None
    created_at: datetime
    published_at: datetime | None


class InstanceCreate(BaseModel):
    template_version_id: UUID
    name: str | None = Field(None, max_length=180)
    zone_id: UUID | None = None
    assignment_mode: LogbookAssignmentMode
    participant_ids: list[UUID] = Field(min_length=1)
    supervisor_id: UUID | None = None
    opens_at: datetime | None = None
    due_at: datetime | None = None
    client_visibility: bool = False

    @model_validator(mode="after")
    def dates(self):
        if self.opens_at and self.due_at and self.due_at <= self.opens_at:
            raise ValueError("due_at must be after opens_at")
        if len(set(self.participant_ids)) != len(self.participant_ids):
            raise ValueError("Duplicate participants")
        return self


class InstanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    template_id: UUID
    template_version_id: UUID
    name: str
    operational_stage: LogbookOperationalStage
    zone_id: UUID | None
    assignment_mode: LogbookAssignmentMode
    opens_at: datetime | None
    due_at: datetime | None
    supervisor_id: UUID | None
    status: LogbookInstanceStatus
    client_visibility: bool
    created_at: datetime


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    logbook_instance_id: UUID
    user_id: UUID
    status: LogbookAssignmentStatus
    started_at: datetime | None
    submitted_at: datetime | None
    approved_at: datetime | None
    review_comment: str | None
    attempt_number: int


class ResponseSave(BaseModel):
    item_id: UUID
    selected_option_id: UUID | None = None
    boolean_value: bool | None = None
    numeric_value: Decimal | None = None
    text_value: str | None = Field(None, max_length=10000)
    is_not_applicable: bool = False
    result_status: LogbookResultStatus
    comment: str | None = Field(None, max_length=5000)
    version: int | None = None


class ResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    assignment_id: UUID
    logbook_item_id: UUID
    selected_option_id: UUID | None
    boolean_value: bool | None
    numeric_value: Decimal | None
    text_value: str | None
    is_not_applicable: bool
    result_status: LogbookResultStatus
    comment: str | None
    completed_by: UUID | None
    completed_at: datetime | None
    version: int


class ReviewIn(BaseModel):
    comment: str | None = Field(None, max_length=5000)


class OptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    label: str
    value: str
    position: int
    is_success_value: bool
    is_failure_value: bool


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str | None
    instructions: str | None
    position: int
    item_type: LogbookItemType
    is_required: bool
    allow_not_applicable: bool
    evidence_policy: LogbookEvidencePolicy
    min_evidences: int
    max_evidences: int
    require_comment_on_failure: bool
    requires_supervisor_review: bool
    client_visible_by_default: bool
    creates_incident_suggestion: bool
    options: list[OptionRead] = []


class SectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str | None
    position: int
    is_required: bool
    items: list[ItemRead] = []


class VersionDetail(VersionRead):
    sections: list[SectionRead] = []


class TemplateDetail(TemplateRead):
    versions: list[VersionRead] = []


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    response_id: UUID
    comment: str | None
    mime_type: str
    file_size: int
    original_filename: str
    client_visible: bool
    created_at: datetime
    deleted_at: datetime | None


class ResponseDetail(ResponseRead):
    evidences: list[EvidenceRead] = []
    completed_by_name: str | None = None
    corrective_incident_id: UUID | None = None
    corrective_task_id: UUID | None = None


class ReviewHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action: str
    previous_status: str | None
    new_status: str
    comment: str | None
    attempt_number: int
    created_at: datetime


class AssignmentDetail(AssignmentRead):
    responses: list[ResponseDetail] = []
    user_name: str | None = None
    history: list[ReviewHistoryRead] = []


class MetricsRead(BaseModel):
    completion_percentage: float
    participation_percentage: float
    approval_percentage: float
    total_participants: int
    pending: int
    in_progress: int
    submitted: int
    changes_requested: int
    approved: int
    total_required_items: int
    completed_items: int
    failed_items: int
    collaborating_participants: int


class InstanceDetail(InstanceRead):
    event_name: str
    version: VersionDetail
    assignments: list[AssignmentDetail]
    metrics: MetricsRead


class InstanceList(BaseModel):
    items: list[InstanceRead]
    total: int
    page: int
    limit: int


class CancelIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class ParticipantsIn(BaseModel):
    user_ids: list[UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_users(self):
        if len(set(self.user_ids)) != len(self.user_ids):
            raise ValueError("Duplicate participants")
        return self


class EvidenceAccess(BaseModel):
    url: str
    expires_in: int


class CorrectiveIncidentIn(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    incident_type: str = Field(default="OTHER", max_length=100)
    priority: PriorityLevel = PriorityLevel.MEDIUM
    assigned_to: UUID | None = None
    evidence_ids: list[UUID] = []


class CorrectiveTaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    assigned_to: UUID
    scheduled_at: datetime | None = None
    priority: PriorityLevel = PriorityLevel.MEDIUM
    evidence_ids: list[UUID] = []


class ClientLogbookSummary(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    operational_stage: LogbookOperationalStage
    status: LogbookInstanceStatus
    completion_percentage: float
    participation_percentage: float
    approval_percentage: float
    total_required_items: int
    completed_items: int
    failed_items: int
    public_evidences: list[EvidenceRead] = []
