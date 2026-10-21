from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentPerson(Base):
    __tablename__ = "document_people"
    __table_args__ = (
        UniqueConstraint("rut_normalized", name="uq_document_people_rut"),
        Index(
            "idx_document_people_email",
            text("lower(email)"),
            postgresql_where=text("email is not null"),
        ),
        Index("idx_document_people_name", "last_name", "first_name"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rut: Mapped[str] = mapped_column(String(16), nullable=False)
    rut_normalized: Mapped[str] = mapped_column(String(12), nullable=False)
    email: Mapped[str | None] = mapped_column(String(180))
    phone: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(String(240))
    commune: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    assignments: Mapped[list["DocumentEmployment"]] = relationship(back_populates="person")
    documents: Mapped[list["ManagedDocument"]] = relationship(back_populates="person")


class DocumentContractDefaults(Base):
    __tablename__ = "document_contract_defaults"

    settings_key: Mapped[str] = mapped_column(String(40), primary_key=True)
    defaults: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )


class EventEppTemplate(Base):
    __tablename__ = "document_event_epp_templates"

    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    items: Mapped[list] = mapped_column(JSONB, nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )


class DocumentEmployment(Base):
    __tablename__ = "document_employments"
    __table_args__ = (
        CheckConstraint(
            "end_date is null or start_date is null or end_date >= start_date",
            name="ck_document_employments_dates",
        ),
        Index("idx_document_employments_person", "person_id", "created_at"),
        Index("idx_document_employments_event", "event_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    person_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_people.id", ondelete="RESTRICT"), nullable=False
    )
    event_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL")
    )
    position: Mapped[str] = mapped_column(String(160), nullable=False)
    area: Mapped[str | None] = mapped_column(String(120))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    remuneration: Mapped[float | None] = mapped_column(Numeric(12, 2))
    workplace: Mapped[str | None] = mapped_column(String(240))
    duties: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    person: Mapped[DocumentPerson] = relationship(back_populates="assignments")


class ManagedDocument(Base):
    __tablename__ = "managed_documents"
    __table_args__ = (
        CheckConstraint("kind in ('CONTRACT', 'EPP')", name="ck_managed_documents_kind"),
        CheckConstraint(
            "status in ('DRAFT', 'READY', 'SENT', 'VIEWED', 'PARTIALLY_SIGNED', 'COMPLETED', 'CANCELLED', 'EXPIRED', 'SUPERSEDED')",
            name="ck_managed_documents_status",
        ),
        Index("idx_managed_documents_client_status", "client_id", "status", "updated_at"),
        Index("idx_managed_documents_event", "event_id"),
        Index("idx_managed_documents_person", "person_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    person_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_people.id", ondelete="RESTRICT"), nullable=False
    )
    employment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_employments.id", ondelete="SET NULL")
    )
    event_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL")
    )
    supersedes_document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="SET NULL")
    )
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="DRAFT")
    signature_method: Mapped[str | None] = mapped_column(String(16))
    paper_status: Mapped[str | None] = mapped_column(String(24))
    paper_printed_at: Mapped[datetime | None] = mapped_column(DateTime)
    paper_printed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    paper_signed_received_at: Mapped[datetime | None] = mapped_column(DateTime)
    paper_signed_received_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    paper_evidence_storage_key: Mapped[str | None] = mapped_column(String(500))
    paper_evidence_sha256: Mapped[str | None] = mapped_column(String(64))
    paper_evidence_content_type: Mapped[str | None] = mapped_column(String(100))
    paper_evidence_file_name: Mapped[str | None] = mapped_column(String(180))
    paper_evidence_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime)
    paper_evidence_uploaded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    frozen_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    original_pdf_key: Mapped[str | None] = mapped_column(String(420))
    signed_pdf_key: Mapped[str | None] = mapped_column(String(420))
    original_sha256: Mapped[str | None] = mapped_column(String(64))
    signed_sha256: Mapped[str | None] = mapped_column(String(64))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    person: Mapped[DocumentPerson] = relationship(back_populates="documents")
    epp_delivery: Mapped["EppDelivery | None"] = relationship(
        back_populates="document", cascade="all, delete-orphan", uselist=False
    )
    signatures: Mapped[list["DocumentSignatureRequest"]] = relationship(back_populates="document")
    paper_batch_items: Mapped[list["DocumentPaperBatchItem"]] = relationship(back_populates="document")


class EppDelivery(Base):
    __tablename__ = "epp_deliveries"
    __table_args__ = (
        Index("idx_epp_deliveries_client_flags", "client_id", "riohs_received", "eirl_completed"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("managed_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    riohs_received: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    eirl_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    delivery_date: Mapped[date | None] = mapped_column(Date)
    supervisor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    document: Mapped[ManagedDocument] = relationship(back_populates="epp_delivery")
    items: Mapped[list["EppDeliveryItem"]] = relationship(
        back_populates="delivery", cascade="all, delete-orphan"
    )


class EppDeliveryItem(Base):
    __tablename__ = "epp_delivery_items"
    __table_args__ = (
        UniqueConstraint("delivery_id", "item_code", name="uq_epp_delivery_items_code"),
        CheckConstraint(
            "returned_at is null or received_at is null or returned_at >= received_at",
            name="ck_epp_delivery_items_dates",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    delivery_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("epp_deliveries.id", ondelete="CASCADE"), nullable=False
    )
    item_code: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    received_at: Mapped[date | None] = mapped_column(Date)
    returned_at: Mapped[date | None] = mapped_column(Date)
    received_conformity: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    delivery: Mapped[EppDelivery] = relationship(back_populates="items")


class DocumentSignatureRequest(Base):
    __tablename__ = "document_signature_requests"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_document_signature_requests_token_hash"),
        Index("idx_document_signature_requests_document", "document_id", "created_at"),
        Index("idx_document_signature_requests_expiry", "expires_at"),
        Index("idx_document_signature_requests_bundle", "bundle_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False
    )
    bundle_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime)
    worker_signed_at: Mapped[datetime | None] = mapped_column(DateTime)
    worker_signed_name: Mapped[str | None] = mapped_column(String(180))
    worker_form_data: Mapped[dict | None] = mapped_column(JSONB)
    supervisor_signed_at: Mapped[datetime | None] = mapped_column(DateTime)
    supervisor_signed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    signature_provider: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="LOCAL_SIMULATED"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    document: Mapped[ManagedDocument] = relationship(back_populates="signatures")


class DocumentEmailBatch(Base):
    __tablename__ = "document_email_batches"
    __table_args__ = (
        Index("idx_document_email_batches_event", "event_id", "created_at"),
        Index("idx_document_email_batches_actor", "created_by", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="QUEUED")
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    items: Mapped[list["DocumentEmailBatchItem"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class DocumentEmailBatchItem(Base):
    __tablename__ = "document_email_batch_items"
    __table_args__ = (
        UniqueConstraint("batch_id", "contract_document_id", name="uq_document_email_batch_contract"),
        Index("idx_document_email_batch_items_queue", "status", "next_attempt_at", "created_at"),
        Index("idx_document_email_batch_items_event", "event_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    batch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_email_batches.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    contract_document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False
    )
    epp_document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="QUEUED")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict | None] = mapped_column(JSONB)
    delivery_payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    batch: Mapped[DocumentEmailBatch] = relationship(back_populates="items")


class DocumentPaperBatch(Base):
    __tablename__ = "document_paper_batches"
    __table_args__ = (
        Index("idx_document_paper_batches_event", "event_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    kinds: Mapped[list] = mapped_column(JSONB, nullable=False)
    people_count: Mapped[int] = mapped_column(Integer, nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    printed_at: Mapped[datetime | None] = mapped_column(DateTime)
    printed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    items: Mapped[list["DocumentPaperBatchItem"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class DocumentPaperBatchItem(Base):
    __tablename__ = "document_paper_batch_items"
    __table_args__ = (
        UniqueConstraint("batch_id", "document_id", name="uq_document_paper_batch_document"),
        Index("idx_document_paper_batch_items_document", "document_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    batch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_paper_batches.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="RESTRICT"), nullable=False
    )
    person_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_people.id", ondelete="RESTRICT"), nullable=False
    )
    document_version: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    batch: Mapped[DocumentPaperBatch] = relationship(back_populates="items")
    document: Mapped[ManagedDocument] = relationship(back_populates="paper_batch_items")
