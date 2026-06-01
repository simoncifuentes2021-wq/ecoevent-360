from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr

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
from app.schemas.common import ORMModel, Timestamped


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: str | None = None
    role: UserRole = UserRole.WORKER
    client_id: UUID | None = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserRead(UserBase, Timestamped):
    id: UUID


class ClientBase(BaseModel):
    business_name: str
    rut: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    address: str | None = None
    industry: str | None = None
    notes: str | None = None
    is_active: bool = True


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    business_name: str | None = None
    rut: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    address: str | None = None
    industry: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class ClientRead(ClientBase, Timestamped):
    id: UUID


class EventBase(BaseModel):
    client_id: UUID
    name: str
    event_type: str | None = None
    description: str | None = None
    location_name: str | None = None
    address: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = "Chile"
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    start_date: datetime
    end_date: datetime
    estimated_attendees: int | None = 0
    real_attendees: int | None = None
    status: EventStatus = EventStatus.QUOTE
    created_by: UUID | None = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    name: str | None = None
    event_type: str | None = None
    description: str | None = None
    location_name: str | None = None
    address: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    estimated_attendees: int | None = None
    real_attendees: int | None = None
    status: EventStatus | None = None


class EventRead(EventBase, Timestamped):
    id: UUID


class ServiceBase(BaseModel):
    name: str
    category: str | None = None
    description: str | None = None
    unit: str | None = None
    base_price: Decimal | None = None
    is_active: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    unit: str | None = None
    base_price: Decimal | None = None
    is_active: bool | None = None


class ServiceRead(ServiceBase, ORMModel):
    id: UUID
    created_at: datetime


class ContractedServiceBase(BaseModel):
    event_id: UUID
    service_id: UUID
    quantity: Decimal | None = 1
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    notes: str | None = None


class ContractedServiceCreate(ContractedServiceBase):
    pass


class ContractedServiceRead(ContractedServiceBase, ORMModel):
    id: UUID
    created_at: datetime


class ZoneBase(BaseModel):
    event_id: UUID
    name: str
    description: str | None = None
    qr_code_url: str | None = None


class ZoneCreate(ZoneBase):
    pass


class ZoneRead(ZoneBase, ORMModel):
    id: UUID
    created_at: datetime


class TaskBase(BaseModel):
    event_id: UUID
    zone_id: UUID | None = None
    assigned_to: UUID | None = None
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: PriorityLevel = PriorityLevel.MEDIUM
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: UUID | None = None


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase, Timestamped):
    id: UUID


class IncidentBase(BaseModel):
    event_id: UUID
    zone_id: UUID | None = None
    reported_by: UUID | None = None
    assigned_to: UUID | None = None
    title: str
    description: str | None = None
    incident_type: str | None = None
    status: IncidentStatus = IncidentStatus.REPORTED
    priority: PriorityLevel = PriorityLevel.MEDIUM
    source: str | None = "INTERNAL"


class IncidentCreate(IncidentBase):
    pass


class IncidentRead(IncidentBase, ORMModel):
    id: UUID
    created_at: datetime
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class EvidenceBase(BaseModel):
    event_id: UUID
    task_id: UUID | None = None
    incident_id: UUID | None = None
    uploaded_by: UUID | None = None
    file_url: str
    file_type: str | None = None
    description: str | None = None
    taken_at: datetime | None = None


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceRead(EvidenceBase, ORMModel):
    id: UUID
    created_at: datetime


class WasteRecordBase(BaseModel):
    event_id: UUID
    zone_id: UUID | None = None
    waste_type_id: UUID | None = None
    weight_kg: Decimal
    destination: WasteDestination
    destination_detail: str | None = None
    recorded_by: UUID | None = None
    evidence_id: UUID | None = None


class WasteRecordCreate(WasteRecordBase):
    pass


class WasteRecordRead(WasteRecordBase, ORMModel):
    id: UUID
    recorded_at: datetime
    created_at: datetime


class CarbonFactorBase(BaseModel):
    category: str
    name: str
    unit: str
    factor_kgco2e: Decimal
    scope: CarbonScope | None = None
    source: str | None = None
    year: int | None = None
    country: str | None = None
    is_active: bool = True


class CarbonFactorCreate(CarbonFactorBase):
    pass


class CarbonFactorRead(CarbonFactorBase, ORMModel):
    id: UUID
    created_at: datetime


class CarbonRecordCreate(BaseModel):
    event_id: UUID
    factor_id: UUID
    category: str
    description: str | None = None
    activity_value: Decimal
    activity_unit: str
    emissions_kgco2e: Decimal
    recorded_by: UUID | None = None


class CarbonRecordRead(CarbonRecordCreate, ORMModel):
    id: UUID
    created_at: datetime


class SurveyImportCreate(BaseModel):
    survey_id: UUID
    file_url: str | None = None
    imported_rows: int = 0
    imported_by: UUID | None = None


class SurveyImportRead(SurveyImportCreate, ORMModel):
    id: UUID
    imported_at: datetime


class DashboardSummary(BaseModel):
    event_id: UUID
    tasks_total: int
    incidents_open: int
    waste_kg: float
    total_kg_co2e: float
