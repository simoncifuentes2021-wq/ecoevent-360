# ruff: noqa: F405
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.core import created_at_column, updated_at_column, uuid_pk
from app.models.enums import *  # noqa: F403


def enum(cls, name):
    return Enum(cls, name=name, create_type=False)


class LogbookTemplate(Base):
    __tablename__ = "logbook_templates"
    __table_args__ = (Index("idx_logbook_templates_status", "status"),)
    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    operational_stage: Mapped[LogbookOperationalStage] = mapped_column(
        enum(LogbookOperationalStage, "logbook_operational_stage"), nullable=False
    )
    status: Mapped[LogbookTemplateStatus] = mapped_column(
        enum(LogbookTemplateStatus, "logbook_template_status"),
        nullable=False,
        server_default=text("'DRAFT'"),
    )
    default_assignment_mode: Mapped[LogbookAssignmentMode] = mapped_column(
        enum(LogbookAssignmentMode, "logbook_assignment_mode"), nullable=False
    )
    default_client_visibility: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    versions: Mapped[list["LogbookTemplateVersion"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class LogbookTemplateVersion(Base):
    __tablename__ = "logbook_template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_logbook_template_version"),
    )
    id: Mapped[UUID] = uuid_pk()
    template_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[LogbookVersionStatus] = mapped_column(
        enum(LogbookVersionStatus, "logbook_version_status"),
        nullable=False,
        server_default=text("'DRAFT'"),
    )
    change_notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    published_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    template: Mapped[LogbookTemplate] = relationship(back_populates="versions")
    sections: Mapped[list["LogbookSection"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", order_by="LogbookSection.position"
    )


class LogbookSection(Base):
    __tablename__ = "logbook_sections"
    __table_args__ = (
        UniqueConstraint("template_version_id", "position", name="uq_logbook_section_position"),
    )
    id: Mapped[UUID] = uuid_pk()
    template_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_template_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = created_at_column()
    version: Mapped[LogbookTemplateVersion] = relationship(back_populates="sections")
    items: Mapped[list["LogbookItem"]] = relationship(
        back_populates="section", cascade="all, delete-orphan", order_by="LogbookItem.position"
    )


class LogbookItem(Base):
    __tablename__ = "logbook_items"
    __table_args__ = (UniqueConstraint("section_id", "position", name="uq_logbook_item_position"),)
    id: Mapped[UUID] = uuid_pk()
    section_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logbook_sections.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[LogbookItemType] = mapped_column(
        enum(LogbookItemType, "logbook_item_type"), nullable=False
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    allow_not_applicable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    evidence_policy: Mapped[LogbookEvidencePolicy] = mapped_column(
        enum(LogbookEvidencePolicy, "logbook_evidence_policy"),
        nullable=False,
        server_default=text("'NONE'"),
    )
    min_evidences: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_evidences: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("5"))
    require_comment_on_failure: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    requires_supervisor_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    client_visible_by_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    creates_incident_suggestion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    created_at: Mapped[datetime] = created_at_column()
    section: Mapped[LogbookSection] = relationship(back_populates="items")
    options: Mapped[list["LogbookItemOption"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="LogbookItemOption.position"
    )


class LogbookItemOption(Base):
    __tablename__ = "logbook_item_options"
    __table_args__ = (
        UniqueConstraint("logbook_item_id", "value", name="uq_logbook_item_option_value"),
    )
    id: Mapped[UUID] = uuid_pk()
    logbook_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logbook_items.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(String(80), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_success_value: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    is_failure_value: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    item: Mapped[LogbookItem] = relationship(back_populates="options")


class LogbookInstance(Base):
    __tablename__ = "logbook_instances"
    __table_args__ = (
        Index("idx_logbook_instances_event", "event_id"),
        Index("idx_logbook_instances_status", "status"),
    )
    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="RESTRICT"), nullable=False
    )
    template_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    template_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_template_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    operational_stage: Mapped[LogbookOperationalStage] = mapped_column(
        enum(LogbookOperationalStage, "logbook_operational_stage"), nullable=False
    )
    zone_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_zones.id", ondelete="SET NULL")
    )
    assignment_mode: Mapped[LogbookAssignmentMode] = mapped_column(
        enum(LogbookAssignmentMode, "logbook_assignment_mode"), nullable=False
    )
    opens_at: Mapped[datetime | None] = mapped_column(DateTime)
    due_at: Mapped[datetime | None] = mapped_column(DateTime)
    supervisor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[LogbookInstanceStatus] = mapped_column(
        enum(LogbookInstanceStatus, "logbook_instance_status"), nullable=False
    )
    client_visibility: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    version: Mapped[LogbookTemplateVersion] = relationship()
    assignments: Mapped[list["LogbookAssignment"]] = relationship(
        back_populates="instance", cascade="all, delete-orphan"
    )


class LogbookAssignment(Base):
    __tablename__ = "logbook_assignments"
    __table_args__ = (
        UniqueConstraint("logbook_instance_id", "user_id", name="uq_logbook_assignment_user"),
    )
    id: Mapped[UUID] = uuid_pk()
    logbook_instance_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logbook_instances.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assignment_role: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'PARTICIPANT'")
    )
    status: Mapped[LogbookAssignmentStatus] = mapped_column(
        enum(LogbookAssignmentStatus, "logbook_assignment_status"),
        nullable=False,
        server_default=text("'PENDING'"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    changes_requested_at: Mapped[datetime | None] = mapped_column(DateTime)
    changes_requested_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    review_comment: Mapped[str | None] = mapped_column(Text)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
    instance: Mapped[LogbookInstance] = relationship(back_populates="assignments")
    responses: Mapped[list["LogbookResponse"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class LogbookResponse(Base):
    __tablename__ = "logbook_responses"
    __table_args__ = (
        UniqueConstraint("assignment_id", "logbook_item_id", name="uq_logbook_response_item"),
    )
    id: Mapped[UUID] = uuid_pk()
    assignment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    logbook_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logbook_items.id", ondelete="RESTRICT"), nullable=False
    )
    selected_option_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logbook_item_options.id", ondelete="RESTRICT")
    )
    boolean_value: Mapped[bool | None] = mapped_column(Boolean)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    text_value: Mapped[str | None] = mapped_column(Text)
    is_not_applicable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    result_status: Mapped[LogbookResultStatus] = mapped_column(
        enum(LogbookResultStatus, "logbook_result_status"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text)
    completed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    assignment: Mapped[LogbookAssignment] = relationship(back_populates="responses")
    evidences: Mapped[list["LogbookEvidence"]] = relationship(back_populates="response")


class LogbookEvidence(Base):
    __tablename__ = "logbook_evidences"
    __table_args__ = (Index("idx_logbook_evidence_response", "response_id"),)
    id: Mapped[UUID] = uuid_pk()
    instance_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_instances.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_assignments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logbook_items.id", ondelete="RESTRICT"), nullable=False
    )
    response_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_responses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    uploaded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    comment: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    client_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    created_at: Mapped[datetime] = created_at_column()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    response: Mapped[LogbookResponse] = relationship(back_populates="evidences")


class LogbookReviewHistory(Base):
    __tablename__ = "logbook_review_history"
    id: Mapped[UUID] = uuid_pk()
    assignment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = created_at_column()


class LogbookIncidentLink(Base):
    __tablename__ = "logbook_incident_links"
    __table_args__ = (UniqueConstraint("response_id", name="uq_logbook_incident_response"),)
    id: Mapped[UUID] = uuid_pk()
    incident_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False
    )
    instance_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_instances.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_assignments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logbook_items.id", ondelete="RESTRICT"), nullable=False
    )
    response_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_responses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    worker_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()


class LogbookTaskLink(Base):
    __tablename__ = "logbook_task_links"
    __table_args__ = (UniqueConstraint("response_id", name="uq_logbook_task_response"),)
    id: Mapped[UUID] = uuid_pk()
    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False
    )
    instance_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_instances.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_assignments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logbook_items.id", ondelete="RESTRICT"), nullable=False
    )
    response_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_responses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()


class LogbookCorrectiveEvidenceLink(Base):
    __tablename__ = "logbook_corrective_evidence_links"
    id: Mapped[UUID] = uuid_pk()
    logbook_evidence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("logbook_evidences.id", ondelete="RESTRICT"),
        nullable=False,
    )
    incident_link_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logbook_incident_links.id", ondelete="CASCADE")
    )
    task_link_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logbook_task_links.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = created_at_column()
