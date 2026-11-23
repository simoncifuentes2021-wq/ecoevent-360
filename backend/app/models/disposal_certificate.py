from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core import created_at_column, uuid_pk


class WasteDisposalCertificate(Base):
    __tablename__ = "waste_disposal_certificates"
    __table_args__ = (
        UniqueConstraint("certificate_number", name="uq_waste_disposal_certificate_number"),
        Index("idx_waste_disposal_certificates_event", "event_id", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    certificate_number: Mapped[str] = mapped_column(String(40), nullable=False)
    certificate_date: Mapped[date] = mapped_column(Date, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    evidence_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("evidences.id", ondelete="SET NULL")
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
    created_at: Mapped[datetime] = created_at_column()
