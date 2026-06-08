from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_event_id", "event_id"),
        Index("idx_audit_logs_client_id", "client_id"),
        Index("idx_audit_logs_task_id", "task_id"),
        Index("idx_audit_logs_incident_id", "incident_id"),
        Index("idx_audit_logs_zone_id", "zone_id"),
        Index("idx_audit_logs_module", "module"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_entity", "entity_type", "entity_id"),
        Index("idx_audit_logs_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    event_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL")
    )
    client_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL")
    )
    task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL")
    )
    incident_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL")
    )
    zone_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_zones.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    module: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(120))
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'SUCCESS'"))
    old_data: Mapped[dict | None] = mapped_column(JSONB)
    new_data: Mapped[dict | None] = mapped_column(JSONB)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(80))
    user_agent: Mapped[str | None] = mapped_column(Text)
    request_method: Mapped[str | None] = mapped_column(String(20))
    request_path: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    user = relationship("User")
    event = relationship("Event")
    client = relationship("Client")
    task = relationship("Task")
    incident = relationship("Incident")
    zone = relationship("EventZone")
