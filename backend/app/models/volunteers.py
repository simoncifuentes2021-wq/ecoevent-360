from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.core import Event, Evidence, WasteType


def _uuid_pk() -> Mapped[UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))


recycling_activation_materials = Table(
    "recycling_activation_materials",
    Base.metadata,
    Column("activation_id", PGUUID(as_uuid=True), ForeignKey("recycling_activations.id", ondelete="CASCADE"), primary_key=True),
    Column("waste_type_id", PGUUID(as_uuid=True), ForeignKey("waste_types.id", ondelete="RESTRICT"), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
)


class Volunteer(Base):
    __tablename__ = "volunteers"
    __table_args__ = (
        UniqueConstraint("email_normalized", name="uq_volunteers_email_normalized"),
        UniqueConstraint("unique_code", name="uq_volunteers_unique_code"),
        CheckConstraint("status in ('ACTIVE','INACTIVE','ARCHIVED')", name="ck_volunteers_status"),
        Index("idx_volunteers_phone_normalized", "phone_normalized"),
        Index("idx_volunteers_status", "status"),
    )

    id: Mapped[UUID] = _uuid_pk()
    full_name: Mapped[str] = mapped_column(String(180), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(254), nullable=False)
    email_lookup_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    phone_normalized: Mapped[str | None] = mapped_column(String(32))
    organization: Mapped[str | None] = mapped_column(String(180))
    unique_code: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ACTIVE")
    consent_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    consent_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str | None] = mapped_column(String(32))
    marketing_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    activations: Mapped[list[VolunteerActivation]] = relationship(back_populates="volunteer")
    contributions: Mapped[list[MaterialContribution]] = relationship(back_populates="volunteer")
    access_tokens: Mapped[list[VolunteerAccessToken]] = relationship(back_populates="volunteer")


class VolunteerActivation(Base):
    __tablename__ = "volunteer_activations"
    __table_args__ = (
        UniqueConstraint("volunteer_id", "activation_id", name="uq_volunteer_activation_person"),
        Index("idx_volunteer_activations_activation", "activation_id", "status"),
        Index("idx_volunteer_activations_volunteer", "volunteer_id", "registered_at"),
        CheckConstraint("status in ('REGISTERED','CHECKED_IN','CANCELLED')", name="ck_volunteer_activations_status"),
    )

    id: Mapped[UUID] = _uuid_pk()
    volunteer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("volunteers.id", ondelete="RESTRICT"), nullable=False)
    activation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("recycling_activations.id", ondelete="RESTRICT"), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="REGISTERED")
    notes: Mapped[str | None] = mapped_column(Text)

    volunteer: Mapped[Volunteer] = relationship(back_populates="activations")
    activation: Mapped[RecyclingActivation] = relationship(back_populates="volunteers")


class RecyclingActivation(Base):
    __tablename__ = "recycling_activations"
    __table_args__ = (
        UniqueConstraint("public_slug", name="uq_recycling_activations_public_slug"),
        Index("idx_recycling_activations_event", "event_id", "status", "starts_at"),
        CheckConstraint("status in ('DRAFT','ACTIVE','CLOSED','CANCELLED','ARCHIVED')", name="ck_recycling_activations_status"),
        CheckConstraint("ends_at is null or ends_at >= starts_at", name="ck_recycling_activations_dates"),
        CheckConstraint("capacity is null or capacity > 0", name="ck_recycling_activations_capacity"),
    )

    id: Mapped[UUID] = _uuid_pk()
    event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="RESTRICT"), nullable=False)
    session_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("event_sessions.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location_name: Mapped[str | None] = mapped_column(String(180))
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responsible_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="DRAFT")
    capacity: Mapped[int | None] = mapped_column()
    public_slug: Mapped[str] = mapped_column(String(72), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    event: Mapped["Event"] = relationship("Event")
    volunteers: Mapped[list[VolunteerActivation]] = relationship(back_populates="activation")
    contributions: Mapped[list[MaterialContribution]] = relationship(back_populates="activation")
    allowed_materials: Mapped[list["WasteType"]] = relationship(
        "WasteType", secondary=recycling_activation_materials
    )
    field_staff_assignments: Mapped[list["FieldStaffActivation"]] = relationship(
        back_populates="activation", cascade="all, delete-orphan"
    )


class FieldStaff(Base):
    __tablename__ = "volunteer_field_staff"
    __table_args__ = (
        UniqueConstraint("event_id", "rut_normalized", name="uq_volunteer_field_staff_event_rut"),
        Index("idx_volunteer_field_staff_event_active", "event_id", "active"),
    )

    id: Mapped[UUID] = _uuid_pk()
    event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(180), nullable=False)
    rut: Mapped[str] = mapped_column(String(16), nullable=False)
    rut_normalized: Mapped[str] = mapped_column(String(12), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    event: Mapped["Event"] = relationship("Event")
    assignments: Mapped[list["FieldStaffActivation"]] = relationship(
        back_populates="field_staff", cascade="all, delete-orphan"
    )


class FieldStaffActivation(Base):
    __tablename__ = "volunteer_field_staff_activations"
    __table_args__ = (Index("idx_volunteer_field_staff_activations_activation", "activation_id"),)

    field_staff_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("volunteer_field_staff.id", ondelete="CASCADE"), primary_key=True)
    activation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("recycling_activations.id", ondelete="CASCADE"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    field_staff: Mapped[FieldStaff] = relationship(back_populates="assignments")
    activation: Mapped[RecyclingActivation] = relationship(back_populates="field_staff_assignments")


class MaterialContribution(Base):
    __tablename__ = "material_contributions"
    __table_args__ = (
        Index("idx_material_contributions_activation_date", "activation_id", "registered_at"),
        Index("idx_material_contributions_volunteer_date", "volunteer_id", "registered_at"),
        Index("idx_material_contributions_status", "status"),
        Index("idx_material_contributions_field_staff", "registered_by_field_staff_id", "registered_at"),
        UniqueConstraint("activation_id", "idempotency_key", name="uq_material_contributions_idempotency"),
        CheckConstraint("status in ('ACTIVE','VOID')", name="ck_material_contributions_status"),
        CheckConstraint("email_status in ('PENDING','SENT','FAILED','SKIPPED')", name="ck_material_contributions_email_status"),
        CheckConstraint("total_weight_kg >= 0", name="ck_material_contributions_total_nonnegative"),
    )

    id: Mapped[UUID] = _uuid_pk()
    volunteer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("volunteers.id", ondelete="RESTRICT"), nullable=False)
    activation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("recycling_activations.id", ondelete="RESTRICT"), nullable=False)
    registered_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    registered_by_field_staff_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("volunteer_field_staff.id", ondelete="SET NULL"))
    updated_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    notes: Mapped[str | None] = mapped_column(Text)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="ACTIVE")
    void_reason: Mapped[str | None] = mapped_column(Text)
    voided_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str | None] = mapped_column(String(80))
    email_status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="PENDING")
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_error: Mapped[str | None] = mapped_column(String(240))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    volunteer: Mapped[Volunteer] = relationship(back_populates="contributions")
    activation: Mapped[RecyclingActivation] = relationship(back_populates="contributions")
    items: Mapped[list[MaterialContributionItem]] = relationship(back_populates="contribution", cascade="all, delete-orphan", order_by="MaterialContributionItem.created_at")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="volunteer_contribution")


class MaterialContributionItem(Base):
    __tablename__ = "material_contribution_items"
    __table_args__ = (
        UniqueConstraint("contribution_id", "material_id", name="uq_material_contribution_material"),
        Index("idx_material_contribution_items_material", "material_id", "contribution_id"),
        CheckConstraint("weight_kg > 0 and weight_kg <= 1000000", name="ck_material_contribution_items_weight_positive"),
    )

    id: Mapped[UUID] = _uuid_pk()
    contribution_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("material_contributions.id", ondelete="CASCADE"), nullable=False)
    material_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("waste_types.id", ondelete="RESTRICT", name="fk_material_contribution_items_waste_type"), nullable=False)
    material_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_snapshot: Mapped[str] = mapped_column(String(8), nullable=False, server_default="kg")
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    contribution: Mapped[MaterialContribution] = relationship(back_populates="items")
    material: Mapped["WasteType"] = relationship("WasteType")


class VolunteerAccessToken(Base):
    __tablename__ = "volunteer_access_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_volunteer_access_tokens_hash"),
        Index("idx_volunteer_access_tokens_volunteer_expiry", "volunteer_id", "expires_at"),
    )

    id: Mapped[UUID] = _uuid_pk()
    volunteer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("volunteers.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    volunteer: Mapped[Volunteer] = relationship(back_populates="access_tokens")
