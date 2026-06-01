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
    PriorityLevel,
    ReportStatus,
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
