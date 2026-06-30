from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    CarbonScope,
    EventStatus,
    IncidentStatus,
    InventoryItemType,
    LogisticsOrderStatus,
    OrderEvidenceStage,
    OrderItemStageStatus,
    OrderStatus,
    PriorityLevel,
    ReportStatus,
    StockMovementType,
    SurveyStatus,
    TaskStatus,
    UserRole,
    WasteDestination,
)


def uuid_pk() -> Mapped[UUID]:
    return mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime, nullable=False, server_default=text("NOW()"))


def updated_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime, nullable=False, server_default=text("NOW()"))


user_role_enum = Enum(UserRole, name="user_role", create_type=False)
event_status_enum = Enum(EventStatus, name="event_status", create_type=False)
task_status_enum = Enum(TaskStatus, name="task_status", create_type=False)
incident_status_enum = Enum(IncidentStatus, name="incident_status", create_type=False)
priority_level_enum = Enum(PriorityLevel, name="priority_level", create_type=False)
waste_destination_enum = Enum(WasteDestination, name="waste_destination", create_type=False)
carbon_scope_enum = Enum(CarbonScope, name="carbon_scope", create_type=False)
survey_status_enum = Enum(SurveyStatus, name="survey_status", create_type=False)
report_status_enum = Enum(ReportStatus, name="report_status", create_type=False)
order_status_enum = Enum(OrderStatus, name="order_status", create_type=False)
order_item_stage_status_enum = Enum(
    OrderItemStageStatus, name="order_item_stage_status", create_type=False
)
order_evidence_stage_enum = Enum(
    OrderEvidenceStage, name="order_evidence_stage", create_type=False
)
inventory_item_type_enum = Enum(InventoryItemType, name="inventory_item_type", create_type=False)
stock_movement_type_enum = Enum(StockMovementType, name="stock_movement_type", create_type=False)
logistics_order_status_enum = Enum(
    LogisticsOrderStatus, name="logistics_order_status", create_type=False
)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[UUID] = uuid_pk()
    business_name: Mapped[str] = mapped_column(String(180), nullable=False)
    rut: Mapped[str | None] = mapped_column(String(30))
    contact_name: Mapped[str | None] = mapped_column(String(160))
    contact_email: Mapped[str | None] = mapped_column(String(180))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    users: Mapped[list["User"]] = relationship(back_populates="client")
    events: Mapped[list["Event"]] = relationship(back_populates="client")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_client_id", "client_id"),
        Index("idx_users_role", "role"),
    )

    id: Mapped[UUID] = uuid_pk()
    client_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL")
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        user_role_enum, nullable=False, server_default=text("'WORKER'")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    client: Mapped[Client | None] = relationship(back_populates="users")
    created_events: Mapped[list["Event"]] = relationship(back_populates="creator")
    event_staff: Mapped[list["EventStaff"]] = relationship(back_populates="user")
    assigned_orders: Mapped[list["EventOrder"]] = relationship(
        back_populates="assignee", foreign_keys="EventOrder.assigned_to"
    )
    warehouse_assignments: Mapped[list["WarehouseUser"]] = relationship(back_populates="user")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_client_id", "client_id"),
        Index("idx_events_status", "status"),
        Index("idx_events_dates", "start_date", "end_date"),
    )

    id: Mapped[UUID] = uuid_pk()
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    location_name: Mapped[str | None] = mapped_column(String(180))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100), server_default=text("'Chile'"))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    estimated_attendees: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    real_attendees: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[EventStatus] = mapped_column(
        event_status_enum, nullable=False, server_default=text("'QUOTE'")
    )
    hidden_from_operations: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    client: Mapped[Client] = relationship(back_populates="events")
    creator: Mapped[User | None] = relationship(back_populates="created_events")
    zones: Mapped[list["EventZone"]] = relationship(back_populates="event")
    event_services: Mapped[list["EventService"]] = relationship(back_populates="event")
    staff_assignments: Mapped[list["EventStaff"]] = relationship(back_populates="event")
    tasks: Mapped[list["Task"]] = relationship(back_populates="event")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="event")
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="event")
    waste_records: Mapped[list["WasteRecord"]] = relationship(back_populates="event")
    carbon_records: Mapped[list["CarbonRecord"]] = relationship(back_populates="event")
    surveys: Mapped[list["Survey"]] = relationship(back_populates="event")
    survey_responses: Mapped[list["SurveyResponse"]] = relationship(back_populates="event")
    reports: Mapped[list["Report"]] = relationship(back_populates="event")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="event")
    orders: Mapped[list["EventOrder"]] = relationship(back_populates="event")
    logistics_orders: Mapped[list["LogisticsOrder"]] = relationship(back_populates="event")


class EventZone(Base):
    __tablename__ = "event_zones"
    __table_args__ = (Index("idx_event_zones_event_id", "event_id"),)

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    qr_code_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship(back_populates="zones")
    tasks: Mapped[list["Task"]] = relationship(back_populates="zone")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="zone")
    evidences_from_responses: Mapped[list["SurveyResponse"]] = relationship(back_populates="zone")
    waste_records: Mapped[list["WasteRecord"]] = relationship(back_populates="zone")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="zone")
    order_items: Mapped[list["EventOrderItem"]] = relationship(back_populates="zone")


class CatalogItem(Base):
    __tablename__ = "catalog_items"
    __table_args__ = (
        Index("idx_catalog_items_category", "category"),
        Index("idx_catalog_items_is_active", "is_active"),
    )

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(50))
    default_unit_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    order_items: Mapped[list["EventOrderItem"]] = relationship(back_populates="catalog_item")


class EventOrder(Base):
    __tablename__ = "event_orders"
    __table_args__ = (
        Index("idx_event_orders_event_id", "event_id"),
        Index("idx_event_orders_assigned_to", "assigned_to"),
        Index("idx_event_orders_status", "status"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    requested_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_to: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[OrderStatus] = mapped_column(
        order_status_enum, nullable=False, server_default=text("'DRAFT'")
    )
    requested_date: Mapped[datetime | None] = mapped_column(DateTime)
    required_date: Mapped[datetime | None] = mapped_column(DateTime)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), server_default=text("0"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    event: Mapped[Event] = relationship(back_populates="orders")
    requester: Mapped[User | None] = relationship(foreign_keys=[requested_by])
    assignee: Mapped[User | None] = relationship(
        back_populates="assigned_orders", foreign_keys=[assigned_to]
    )
    items: Mapped[list["EventOrderItem"]] = relationship(back_populates="order")
    evidences: Mapped[list["OrderEvidence"]] = relationship(back_populates="order")


class EventOrderItem(Base):
    __tablename__ = "event_order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0"),
        CheckConstraint("unit_price >= 0"),
        Index("idx_event_order_items_order_id", "order_id"),
        Index("idx_event_order_items_catalog_item_id", "catalog_item_id"),
        Index("idx_event_order_items_zone_id", "zone_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_orders.id", ondelete="CASCADE"), nullable=False
    )
    catalog_item_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("catalog_items.id", ondelete="SET NULL")
    )
    zone_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_zones.id", ondelete="SET NULL")
    )
    item_name_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), server_default=text("0"))
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), server_default=text("0"))
    notes: Mapped[str | None] = mapped_column(Text)
    load_status: Mapped[OrderItemStageStatus] = mapped_column(
        order_item_stage_status_enum, nullable=False, server_default=text("'PENDING'")
    )
    delivery_status: Mapped[OrderItemStageStatus] = mapped_column(
        order_item_stage_status_enum, nullable=False, server_default=text("'PENDING'")
    )
    return_status: Mapped[OrderItemStageStatus] = mapped_column(
        order_item_stage_status_enum, nullable=False, server_default=text("'PENDING'")
    )
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime)
    loaded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    delivered_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    returned_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    load_observation: Mapped[str | None] = mapped_column(Text)
    delivery_observation: Mapped[str | None] = mapped_column(Text)
    return_observation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    order: Mapped[EventOrder] = relationship(back_populates="items")
    catalog_item: Mapped[CatalogItem | None] = relationship(back_populates="order_items")
    zone: Mapped[EventZone | None] = relationship(back_populates="order_items")
    evidences: Mapped[list["OrderEvidence"]] = relationship(back_populates="order_item")


class OrderEvidence(Base):
    __tablename__ = "order_evidences"
    __table_args__ = (
        Index("idx_order_evidences_event_id", "event_id"),
        Index("idx_order_evidences_order_id", "order_id"),
        Index("idx_order_evidences_order_item_id", "order_item_id"),
        Index("idx_order_evidences_stage", "stage"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_orders.id", ondelete="CASCADE"), nullable=False
    )
    order_item_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_order_items.id", ondelete="SET NULL")
    )
    uploaded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    stage: Mapped[OrderEvidenceStage] = mapped_column(order_evidence_stage_enum, nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(80))
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_size: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    visible_to_client: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship()
    order: Mapped[EventOrder] = relationship(back_populates="evidences")
    order_item: Mapped[EventOrderItem | None] = relationship(back_populates="evidences")
    uploader: Mapped[User | None] = relationship()


class Warehouse(Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        Index("idx_warehouses_is_active", "is_active"),
        Index("idx_warehouses_city", "city"),
    )

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    users: Mapped[list["WarehouseUser"]] = relationship(back_populates="warehouse")
    stock_balances: Mapped[list["StockBalance"]] = relationship(back_populates="warehouse")
    stock_movements: Mapped[list["StockMovement"]] = relationship(back_populates="warehouse")


class WarehouseUser(Base):
    __tablename__ = "warehouse_users"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "user_id"),
        Index("idx_warehouse_users_warehouse_id", "warehouse_id"),
        Index("idx_warehouse_users_user_id", "user_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    warehouse_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    can_view_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    can_manage_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    can_dispatch_orders: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = created_at_column()

    warehouse: Mapped[Warehouse] = relationship(back_populates="users")
    user: Mapped[User] = relationship(back_populates="warehouse_assignments")


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint("unit_price >= 0"),
        CheckConstraint("replacement_cost >= 0"),
        CheckConstraint("min_stock >= 0"),
        Index("idx_inventory_items_sku", "sku"),
        Index("idx_inventory_items_item_type", "item_type"),
        Index("idx_inventory_items_is_active", "is_active"),
    )

    id: Mapped[UUID] = uuid_pk()
    sku: Mapped[str | None] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    item_type: Mapped[InventoryItemType] = mapped_column(inventory_item_type_enum, nullable=False)
    return_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    unit: Mapped[str | None] = mapped_column(String(50))
    # Future order flow: copy this to logistics_order_items.unit_price_snapshot and
    # calculate total_price = quantity_requested * unit_price_snapshot.
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    replacement_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    min_stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    creator: Mapped[User | None] = relationship()
    stock_balances: Mapped[list["StockBalance"]] = relationship(back_populates="item")
    stock_movements: Mapped[list["StockMovement"]] = relationship(back_populates="item")
    logistics_order_items: Mapped[list["LogisticsOrderItem"]] = relationship(back_populates="item")


class StockBalance(Base):
    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "item_id"),
        CheckConstraint("quantity_on_hand >= 0"),
        CheckConstraint("quantity_reserved >= 0"),
        CheckConstraint("quantity_damaged >= 0"),
        CheckConstraint("quantity_reserved <= quantity_on_hand"),
        CheckConstraint("quantity_damaged <= quantity_on_hand"),
        CheckConstraint("(quantity_on_hand - quantity_reserved - quantity_damaged) >= 0"),
        Index("idx_stock_balances_warehouse_id", "warehouse_id"),
        Index("idx_stock_balances_item_id", "item_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    warehouse_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    quantity_on_hand: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    quantity_reserved: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    quantity_damaged: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    warehouse: Mapped[Warehouse] = relationship(back_populates="stock_balances")
    item: Mapped[InventoryItem] = relationship(back_populates="stock_balances")
    movements: Mapped[list["StockMovement"]] = relationship(back_populates="stock_balance")


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity > 0"),
        Index("idx_stock_movements_warehouse_id", "warehouse_id"),
        Index("idx_stock_movements_item_id", "item_id"),
        Index("idx_stock_movements_stock_balance_id", "stock_balance_id"),
        Index("idx_stock_movements_movement_type", "movement_type"),
        Index("idx_stock_movements_created_at", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    warehouse_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    stock_balance_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stock_balances.id", ondelete="SET NULL")
    )
    movement_type: Mapped[StockMovementType] = mapped_column(
        stock_movement_type_enum, nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    previous_quantity_on_hand: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    new_quantity_on_hand: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    previous_quantity_reserved: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    new_quantity_reserved: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    previous_quantity_damaged: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    new_quantity_damaged: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    reference_type: Mapped[str | None] = mapped_column(String(80))
    reference_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()

    warehouse: Mapped[Warehouse] = relationship(back_populates="stock_movements")
    item: Mapped[InventoryItem] = relationship(back_populates="stock_movements")
    stock_balance: Mapped[StockBalance | None] = relationship(back_populates="movements")
    creator: Mapped[User | None] = relationship()


class LogisticsOrder(Base):
    __tablename__ = "logistics_orders"
    __table_args__ = (
        Index("idx_logistics_orders_event_id", "event_id"),
        Index("idx_logistics_orders_warehouse_id", "warehouse_id"),
        Index("idx_logistics_orders_assigned_operator_id", "assigned_operator_id"),
        Index("idx_logistics_orders_status", "status"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    requested_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_operator_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[LogisticsOrderStatus] = mapped_column(
        logistics_order_status_enum, nullable=False, server_default=text("'REQUESTED'")
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    delivery_zone: Mapped[str | None] = mapped_column(String(180))
    delivery_notes: Mapped[str | None] = mapped_column(Text)
    total_estimated_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime)
    reserved_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime)
    prepared_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime)
    dispatched_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    dispatch_notes: Mapped[str | None] = mapped_column(Text)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    outcome_recorded_at: Mapped[datetime | None] = mapped_column(DateTime)
    outcome_recorded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    outcome_notes: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    closure_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    event: Mapped[Event] = relationship(back_populates="logistics_orders")
    warehouse: Mapped[Warehouse] = relationship()
    requester: Mapped[User] = relationship(foreign_keys=[requested_by])
    assigned_operator: Mapped[User] = relationship(foreign_keys=[assigned_operator_id])
    reserver: Mapped[User | None] = relationship(foreign_keys=[reserved_by])
    preparer: Mapped[User | None] = relationship(foreign_keys=[prepared_by])
    dispatcher: Mapped[User | None] = relationship(foreign_keys=[dispatched_by])
    deliverer: Mapped[User | None] = relationship(foreign_keys=[delivered_by])
    outcome_recorder: Mapped[User | None] = relationship(foreign_keys=[outcome_recorded_by])
    closer: Mapped[User | None] = relationship(foreign_keys=[closed_by])
    items: Mapped[list["LogisticsOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class LogisticsOrderItem(Base):
    __tablename__ = "logistics_order_items"
    __table_args__ = (
        CheckConstraint("quantity_requested > 0"),
        CheckConstraint("quantity_reserved >= 0"),
        CheckConstraint("quantity_missing >= 0"),
        CheckConstraint("quantity_reserved <= quantity_requested"),
        CheckConstraint("quantity_loaded >= 0"),
        CheckConstraint("quantity_dispatched >= 0"),
        CheckConstraint("quantity_loaded <= quantity_reserved"),
        CheckConstraint("quantity_dispatched <= quantity_loaded"),
        CheckConstraint("quantity_delivered >= 0"),
        CheckConstraint("quantity_delivered <= quantity_dispatched"),
        CheckConstraint("quantity_consumed >= 0"),
        CheckConstraint("quantity_returned >= 0"),
        CheckConstraint("quantity_returned_damaged >= 0"),
        CheckConstraint("quantity_lost >= 0"),
        CheckConstraint("quantity_discarded >= 0"),
        CheckConstraint(
            "(quantity_consumed + quantity_returned + quantity_returned_damaged + quantity_lost + quantity_discarded) <= quantity_delivered"
        ),
        CheckConstraint("unit_price_snapshot >= 0"),
        CheckConstraint("total_price >= 0"),
        Index("idx_logistics_order_items_order_id", "order_id"),
        Index("idx_logistics_order_items_item_id", "item_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("logistics_orders.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False
    )
    item_name_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)
    item_type_snapshot: Mapped[str] = mapped_column(String(60), nullable=False)
    unit_snapshot: Mapped[str | None] = mapped_column(String(50))
    quantity_requested: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_reserved: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    quantity_missing: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    reservation_status: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'PENDING'")
    )
    quantity_loaded: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    quantity_dispatched: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    preparation_status: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'PENDING'")
    )
    quantity_delivered: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    delivery_status: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'PENDING'")
    )
    quantity_consumed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    quantity_returned: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    quantity_returned_damaged: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    quantity_lost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    quantity_discarded: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    outcome_status: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default=text("'PENDING'")
    )
    outcome_notes: Mapped[str | None] = mapped_column(Text)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    order: Mapped[LogisticsOrder] = relationship(back_populates="items")
    item: Mapped[InventoryItem] = relationship(back_populates="logistics_order_items")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(50))
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = created_at_column()

    event_services: Mapped[list["EventService"]] = relationship(back_populates="service")


class EventService(Base):
    __tablename__ = "event_services"
    __table_args__ = (
        Index("idx_event_services_event_id", "event_id"),
        Index("idx_event_services_service_id", "service_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    service_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), server_default=text("1"))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship(back_populates="event_services")
    service: Mapped[Service] = relationship(back_populates="event_services")


class EventStaff(Base):
    __tablename__ = "event_staff"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id"),
        Index("idx_event_staff_event_id", "event_id"),
        Index("idx_event_staff_user_id", "user_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_in_event: Mapped[str | None] = mapped_column(String(100))
    shift_start: Mapped[datetime | None] = mapped_column(DateTime)
    shift_end: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship(back_populates="staff_assignments")
    user: Mapped[User] = relationship(back_populates="event_staff")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("idx_tasks_event_id", "event_id"),
        Index("idx_tasks_zone_id", "zone_id"),
        Index("idx_tasks_assigned_to", "assigned_to"),
        Index("idx_tasks_status", "status"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    zone_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_zones.id", ondelete="SET NULL")
    )
    assigned_to: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        task_status_enum, nullable=False, server_default=text("'PENDING'")
    )
    priority: Mapped[PriorityLevel] = mapped_column(
        priority_level_enum, nullable=False, server_default=text("'MEDIUM'")
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    event: Mapped[Event] = relationship(back_populates="tasks")
    zone: Mapped[EventZone | None] = relationship(back_populates="tasks")
    assignee: Mapped[User | None] = relationship(foreign_keys=[assigned_to])
    creator: Mapped[User | None] = relationship(foreign_keys=[created_by])
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="task")


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("idx_incidents_event_id", "event_id"),
        Index("idx_incidents_zone_id", "zone_id"),
        Index("idx_incidents_status", "status"),
        Index("idx_incidents_priority", "priority"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    zone_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_zones.id", ondelete="SET NULL")
    )
    reported_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_to: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    incident_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[IncidentStatus] = mapped_column(
        incident_status_enum, nullable=False, server_default=text("'REPORTED'")
    )
    priority: Mapped[PriorityLevel] = mapped_column(
        priority_level_enum, nullable=False, server_default=text("'MEDIUM'")
    )
    source: Mapped[str | None] = mapped_column(String(80), server_default=text("'INTERNAL'"))
    created_at: Mapped[datetime] = created_at_column()
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    event: Mapped[Event] = relationship(back_populates="incidents")
    zone: Mapped[EventZone | None] = relationship(back_populates="incidents")
    reporter: Mapped[User | None] = relationship(foreign_keys=[reported_by])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assigned_to])
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="incident")


class Evidence(Base):
    __tablename__ = "evidences"
    __table_args__ = (
        Index("idx_evidences_event_id", "event_id"),
        Index("idx_evidences_task_id", "task_id"),
        Index("idx_evidences_incident_id", "incident_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL")
    )
    incident_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL")
    )
    uploaded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship(back_populates="evidences")
    task: Mapped[Task | None] = relationship(back_populates="evidences")
    incident: Mapped[Incident | None] = relationship(back_populates="evidences")
    uploader: Mapped[User | None] = relationship()
    waste_records: Mapped[list["WasteRecord"]] = relationship(back_populates="evidence")


class WasteType(Base):
    __tablename__ = "waste_types"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_recyclable: Mapped[bool | None] = mapped_column(Boolean, server_default=text("FALSE"))
    created_at: Mapped[datetime] = created_at_column()

    waste_records: Mapped[list["WasteRecord"]] = relationship(back_populates="waste_type")


class WasteRecord(Base):
    __tablename__ = "waste_records"
    __table_args__ = (
        CheckConstraint("weight_kg >= 0"),
        Index("idx_waste_records_event_id", "event_id"),
        Index("idx_waste_records_type_id", "waste_type_id"),
        Index("idx_waste_records_destination", "destination"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    zone_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_zones.id", ondelete="SET NULL")
    )
    waste_type_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("waste_types.id", ondelete="RESTRICT")
    )
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    destination: Mapped[WasteDestination] = mapped_column(waste_destination_enum, nullable=False)
    destination_detail: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    evidence_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("evidences.id", ondelete="SET NULL")
    )
    recorded_at: Mapped[datetime] = created_at_column()
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship(back_populates="waste_records")
    zone: Mapped[EventZone | None] = relationship(back_populates="waste_records")
    waste_type: Mapped[WasteType | None] = relationship(back_populates="waste_records")
    recorder: Mapped[User | None] = relationship()
    evidence: Mapped[Evidence | None] = relationship(back_populates="waste_records")


class CarbonFactor(Base):
    __tablename__ = "carbon_factors"
    __table_args__ = (CheckConstraint("factor_kgco2e >= 0"),)

    id: Mapped[UUID] = uuid_pk()
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    factor_kgco2e: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    scope: Mapped[CarbonScope | None] = mapped_column(carbon_scope_enum)
    source: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer)
    country: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = created_at_column()

    carbon_records: Mapped[list["CarbonRecord"]] = relationship(back_populates="factor")


class CarbonRecord(Base):
    __tablename__ = "carbon_records"
    __table_args__ = (
        CheckConstraint("activity_value >= 0"),
        CheckConstraint("emissions_kgco2e >= 0"),
        Index("idx_carbon_records_event_id", "event_id"),
        Index("idx_carbon_records_factor_id", "factor_id"),
        Index("idx_carbon_records_category", "category"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    factor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("carbon_factors.id", ondelete="RESTRICT"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    activity_value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    activity_unit: Mapped[str] = mapped_column(String(50), nullable=False)
    emissions_kgco2e: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    recorded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship(back_populates="carbon_records")
    factor: Mapped[CarbonFactor] = relationship(back_populates="carbon_records")
    recorder: Mapped[User | None] = relationship()


class FuelRecord(Base):
    __tablename__ = "fuel_records"
    __table_args__ = (
        CheckConstraint("liters >= 0"),
        CheckConstraint("kilometers >= 0"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    vehicle_name: Mapped[str | None] = mapped_column(String(160))
    vehicle_plate: Mapped[str | None] = mapped_column(String(40))
    fuel_type: Mapped[str | None] = mapped_column(String(80))
    liters: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    kilometers: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    trips: Mapped[int | None] = mapped_column(Integer, server_default=text("1"))
    recorded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship()
    recorder: Mapped[User | None] = relationship()


class EnergyRecord(Base):
    __tablename__ = "energy_records"
    __table_args__ = (CheckConstraint("kwh >= 0"),)

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(100))
    kwh: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    hours_used: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship()
    recorder: Mapped[User | None] = relationship()


class WaterRecord(Base):
    __tablename__ = "water_records"
    __table_args__ = (CheckConstraint("liters >= 0"),)

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(100))
    liters: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    usage_type: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship()
    recorder: Mapped[User | None] = relationship()


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    google_form_url: Mapped[str | None] = mapped_column(Text)
    google_sheet_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SurveyStatus] = mapped_column(
        survey_status_enum, nullable=False, server_default=text("'DRAFT'")
    )
    opens_at: Mapped[datetime | None] = mapped_column(DateTime)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    event: Mapped[Event] = relationship(back_populates="surveys")
    imports: Mapped[list["SurveyImport"]] = relationship(back_populates="survey")
    responses: Mapped[list["SurveyResponse"]] = relationship(back_populates="survey")


class SurveyImport(Base):
    __tablename__ = "survey_imports"

    id: Mapped[UUID] = uuid_pk()
    survey_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )
    file_url: Mapped[str | None] = mapped_column(Text)
    imported_rows: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    imported_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    survey: Mapped[Survey] = relationship(back_populates="imports")
    importer: Mapped[User | None] = relationship()


class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    __table_args__ = (
        Index("idx_survey_responses_survey_id", "survey_id"),
        Index("idx_survey_responses_event_id", "event_id"),
        Index("idx_survey_responses_zone_id", "zone_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    survey_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    zone_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_zones.id", ondelete="SET NULL")
    )
    response_external_id: Mapped[str | None] = mapped_column(String(180))
    response_date: Mapped[datetime | None] = mapped_column(DateTime)
    age_range: Mapped[str | None] = mapped_column(String(80))
    origin_commune: Mapped[str | None] = mapped_column(String(120))
    transport_mode: Mapped[str | None] = mapped_column(String(120))
    cleanliness_rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    bathroom_rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    recycling_visibility: Mapped[str | None] = mapped_column(String(80))
    separated_waste: Mapped[bool | None] = mapped_column(Boolean)
    general_rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    would_recommend: Mapped[bool | None] = mapped_column(Boolean)
    main_problem: Mapped[str | None] = mapped_column(String(160))
    comments: Mapped[str | None] = mapped_column(Text)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_column()

    survey: Mapped[Survey] = relationship(back_populates="responses")
    event: Mapped[Event] = relationship(back_populates="survey_responses")
    zone: Mapped[EventZone | None] = relationship(back_populates="evidences_from_responses")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("idx_alerts_event_id", "event_id"),
        Index("idx_alerts_status", "status"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    zone_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("event_zones.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    alert_type: Mapped[str | None] = mapped_column(String(100))
    priority: Mapped[PriorityLevel] = mapped_column(
        priority_level_enum, nullable=False, server_default=text("'MEDIUM'")
    )
    status: Mapped[str] = mapped_column(String(80), nullable=False, server_default=text("'OPEN'"))
    generated_from: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = created_at_column()
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    event: Mapped[Event] = relationship(back_populates="alerts")
    zone: Mapped[EventZone | None] = relationship(back_populates="alerts")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("idx_reports_event_id", "event_id"),
        Index("idx_reports_status", "status"),
    )

    id: Mapped[UUID] = uuid_pk()
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    pdf_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportStatus] = mapped_column(
        report_status_enum, nullable=False, server_default=text("'DRAFT'")
    )
    generated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_column()

    event: Mapped[Event] = relationship(back_populates="reports")
    generator: Mapped[User | None] = relationship()
