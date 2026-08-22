from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
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
from app.models.core import created_at_column, updated_at_column, uuid_pk
from app.models.enums import (
    EnvironmentalActionStatus,
    EnvironmentalActionType,
    EnvironmentalEnergySource,
    EnvironmentalEnergyInputMode,
    EnvironmentalMetricKey,
    EnvironmentalReviewDecision,
    EnvironmentalReviewStatus,
)


class EnvironmentalFactor(Base):
    __tablename__ = "environmental_factors"
    __table_args__ = (
        CheckConstraint("factor_value >= 0", name="ck_environmental_factor_nonnegative"),
        Index(
            "idx_environmental_factors_lookup",
            "impact_type",
            "technology",
            "unit_basis",
            "is_active",
        ),
    )
    id: Mapped[UUID] = uuid_pk()
    impact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    technology: Mapped[str] = mapped_column(String(120), nullable=False)
    pollutant: Mapped[str | None] = mapped_column(String(30))
    unit_basis: Mapped[str] = mapped_column(String(50), nullable=False)
    factor_value: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    factor_unit: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    country: Mapped[str | None] = mapped_column(String(100))
    methodology: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class EnvironmentalMethodology(Base):
    __tablename__ = "environmental_methodologies"
    __table_args__ = (
        Index("idx_environmental_methodologies_type_active", "action_type", "is_active"),
    )
    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    action_type: Mapped[EnvironmentalActionType] = mapped_column(
        Enum(EnvironmentalActionType, native_enum=False, create_constraint=False), nullable=False
    )
    baseline_technology: Mapped[str] = mapped_column(String(180), nullable=False)
    actual_technology: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class EcoEquivalenceFactor(Base):
    __tablename__ = "eco_equivalence_factors"
    __table_args__ = (
        UniqueConstraint("key", name="uq_eco_equivalence_factors_key"),
        CheckConstraint("factor >= 0", name="ck_eco_equivalence_factor_nonnegative"),
    )
    id: Mapped[UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    metric_source: Mapped[EnvironmentalMetricKey] = mapped_column(
        Enum(EnvironmentalMetricKey, native_enum=False, create_constraint=False), nullable=False
    )
    factor: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    unit: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class EnvironmentalAction(Base):
    __tablename__ = "environmental_actions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id", "session_id"],
            ["event_sessions.event_id", "event_sessions.id"],
            name="fk_environmental_action_event_session",
            ondelete="CASCADE",
        ),
        CheckConstraint("quantity_used > 0", name="ck_environmental_action_quantity_positive"),
        CheckConstraint(
            "hours_used is null or hours_used >= 0",
            name="ck_environmental_action_hours_nonnegative",
        ),
        CheckConstraint(
            "distance_km is null or distance_km >= 0",
            name="ck_environmental_action_distance_nonnegative",
        ),
        CheckConstraint(
            "energy_kwh is null or energy_kwh >= 0",
            name="ck_environmental_action_energy_nonnegative",
        ),
        CheckConstraint(
            "energy_per_unit_hour_kwh is null or energy_per_unit_hour_kwh > 0",
            name="ck_environmental_action_energy_per_unit_hour_positive",
        ),
        CheckConstraint(
            "energy_input_mode != 'PER_UNIT_HOUR' or (energy_per_unit_hour_kwh is not null and hours_used > 0)",
            name="ck_environmental_action_per_unit_hour_complete",
        ),
        CheckConstraint(
            "power_kw is null or power_kw >= 0", name="ck_environmental_action_power_nonnegative"
        ),
        Index("idx_environmental_actions_event_id", "event_id"),
        Index("idx_environmental_actions_session_id", "session_id"),
        Index("idx_environmental_actions_methodology_id", "methodology_id"),
    )
    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    methodology_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("environmental_methodologies.id", ondelete="RESTRICT")
    )
    action_type: Mapped[EnvironmentalActionType] = mapped_column(
        Enum(EnvironmentalActionType, native_enum=False, create_constraint=False), nullable=False
    )
    status: Mapped[EnvironmentalActionStatus] = mapped_column(
        Enum(EnvironmentalActionStatus, native_enum=False, create_constraint=False),
        nullable=False,
        server_default=text("'INCOMPLETE'"),
    )
    review_status: Mapped[EnvironmentalReviewStatus] = mapped_column(
        Enum(EnvironmentalReviewStatus, native_enum=False, create_constraint=False),
        nullable=False,
        server_default=text("'DRAFT'"),
    )
    review_revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    submitted_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    review_comment: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    quantity_used: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    hours_used: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(16, 4))
    energy_kwh: Mapped[Decimal | None] = mapped_column(Numeric(16, 6))
    energy_per_unit_hour_kwh: Mapped[Decimal | None] = mapped_column(Numeric(16, 6))
    energy_input_mode: Mapped[EnvironmentalEnergyInputMode] = mapped_column(
        Enum(EnvironmentalEnergyInputMode, native_enum=False, create_constraint=False),
        nullable=False,
        server_default=text("'TOTAL_MEASURED'"),
    )
    power_kw: Mapped[Decimal | None] = mapped_column(Numeric(16, 6))
    energy_source: Mapped[EnvironmentalEnergySource | None] = mapped_column(
        Enum(EnvironmentalEnergySource, native_enum=False, create_constraint=False)
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
    methodology: Mapped[EnvironmentalMethodology | None] = relationship()
    metrics: Mapped[list["EnvironmentalActionMetric"]] = relationship(
        back_populates="action", cascade="all, delete-orphan"
    )
    review_history: Mapped[list["EnvironmentalActionReview"]] = relationship(
        back_populates="action", cascade="all, delete-orphan", order_by="EnvironmentalActionReview.created_at"
    )


class EnvironmentalActionReview(Base):
    __tablename__ = "environmental_action_reviews"
    __table_args__ = (Index("idx_environmental_action_reviews_action_id", "action_id"),)
    id: Mapped[UUID] = uuid_pk()
    action_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("environmental_actions.id", ondelete="CASCADE"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[EnvironmentalReviewDecision] = mapped_column(
        Enum(EnvironmentalReviewDecision, native_enum=False, create_constraint=False), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    action: Mapped[EnvironmentalAction] = relationship(back_populates="review_history")


class EnvironmentalActionMetric(Base):
    __tablename__ = "environmental_action_metrics"
    __table_args__ = (
        UniqueConstraint("action_id", "metric_key", name="uq_environmental_action_metric_key"),
        Index("idx_environmental_action_metrics_action_id", "action_id"),
        CheckConstraint(
            "reported_value is null or override_reason is not null",
            name="ck_environmental_metric_override_reason",
        ),
    )
    id: Mapped[UUID] = uuid_pk()
    action_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("environmental_actions.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_key: Mapped[EnvironmentalMetricKey] = mapped_column(
        Enum(EnvironmentalMetricKey, native_enum=False, create_constraint=False), nullable=False
    )
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    calculated_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    reported_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    is_manual_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    override_reason: Mapped[str | None] = mapped_column(Text)
    calculation_method: Mapped[str] = mapped_column(Text, nullable=False)
    calculation_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = updated_at_column()
    action: Mapped[EnvironmentalAction] = relationship(back_populates="metrics")

    @property
    def value(self) -> Decimal | None:
        return self.reported_value if self.is_manual_override else self.calculated_value
