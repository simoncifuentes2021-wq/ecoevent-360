from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint("status in ('DRAFT','APPROVED','SENT','PARTIALLY_RECEIVED','RECEIVED','CANCELLED')", name="ck_purchase_orders_status"),
        CheckConstraint("subtotal >= 0", name="ck_purchase_orders_subtotal_nonnegative"),
        CheckConstraint("tax_total >= 0", name="ck_purchase_orders_tax_nonnegative"),
        CheckConstraint("total >= 0", name="ck_purchase_orders_total_nonnegative"),
        Index("idx_purchase_orders_event_id", "event_id"),
        Index("idx_purchase_orders_status", "status"),
        Index("idx_purchase_orders_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    order_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="DRAFT")
    event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"))
    event_name_snapshot: Mapped[str | None] = mapped_column(String(180))
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(180), nullable=False)
    supplier_rut: Mapped[str | None] = mapped_column(String(30))
    supplier_email: Mapped[str | None] = mapped_column(String(180))
    supplier_phone: Mapped[str | None] = mapped_column(String(50))
    supplier_address: Mapped[str | None] = mapped_column(Text)
    delivery_address: Mapped[str | None] = mapped_column(Text)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    required_date: Mapped[date | None] = mapped_column(Date)
    payment_terms: Mapped[str | None] = mapped_column(String(240))
    notes: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="CLP")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    tax_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    approved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    sent_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    pdf_storage_key: Mapped[str | None] = mapped_column(Text)
    pdf_sha256: Mapped[str | None] = mapped_column(String(64))
    pdf_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("NOW()"))

    event = relationship("Event")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    sender = relationship("User", foreign_keys=[sent_by])
    items: Mapped[list["PurchaseOrderItem"]] = relationship(back_populates="purchase_order", cascade="all, delete-orphan", order_by="PurchaseOrderItem.line_number")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        CheckConstraint("line_number > 0", name="ck_purchase_order_items_line_positive"),
        CheckConstraint("quantity > 0", name="ck_purchase_order_items_quantity_positive"),
        CheckConstraint("received_quantity >= 0", name="ck_purchase_order_items_received_nonnegative"),
        CheckConstraint("unit_price >= 0", name="ck_purchase_order_items_price_nonnegative"),
        CheckConstraint("tax_rate >= 0 and tax_rate <= 100", name="ck_purchase_order_items_tax_rate"),
        CheckConstraint("line_subtotal >= 0 and line_tax >= 0 and line_total >= 0", name="ck_purchase_order_items_totals_nonnegative"),
        Index("idx_purchase_order_items_order_id", "purchase_order_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    purchase_order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False, server_default="unidad")
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, server_default="0")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default="19")
    line_subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    line_tax: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("NOW()"))

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="items")
