from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core import created_at_column, updated_at_column


class GoogleCalendarConnection(Base):
    """Single Google Calendar connection used by the Super Admin integration."""

    __tablename__ = "google_calendar_connections"

    connection_key: Mapped[str] = mapped_column(String(24), primary_key=True)
    account_email: Mapped[str] = mapped_column(String(320), nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    granted_scopes: Mapped[str] = mapped_column(Text, nullable=False)
    connected_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    connected_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
