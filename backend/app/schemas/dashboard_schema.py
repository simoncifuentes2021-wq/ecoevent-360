from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import EventStatus, IncidentStatus, PriorityLevel, TaskStatus


class DashboardBucket(BaseModel):
    name: str
    value: float


class DashboardClient(BaseModel):
    id: UUID
    business_name: str


class DashboardEvent(BaseModel):
    id: UUID
    client_id: UUID
    name: str
    event_type: str | None = None
    client_name: str | None = None
    status: EventStatus
    start_date: datetime
    end_date: datetime
    estimated_attendees: int | None = None
    real_attendees: int | None = None
    location_name: str | None = None
    hidden_from_operations: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DashboardIncident(BaseModel):
    id: UUID
    event_id: UUID
    event_name: str | None = None
    zone_name: str | None = None
    title: str
    priority: PriorityLevel
    status: IncidentStatus | str
    created_at: datetime


class DashboardTaskItem(BaseModel):
    id: UUID
    event_id: UUID
    event_name: str | None = None
    zone_name: str | None = None
    title: str
    status: TaskStatus
    priority: PriorityLevel
    scheduled_at: datetime | None = None


class DashboardReport(BaseModel):
    id: UUID
    event_id: UUID
    event_name: str | None = None
    title: str
    status: str
    pdf_url: str | None = None
    generated_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime | None = None


class AdminDashboardResponse(BaseModel):
    total_clients: int = 0
    total_users: int = 0
    total_events: int = 0
    active_events: int = 0
    finished_events: int = 0
    cancelled_events: int = 0
    open_incidents: int = 0
    resolved_incidents: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0
    completed_tasks_rate: float = 0
    total_waste_kg: float = 0
    recovered_waste_kg: float = 0
    waste_recovery_rate: float = 0
    total_carbon_kgco2e: float = 0
    total_carbon_tco2e: float = 0
    latest_events: list[DashboardEvent] = []
    latest_incidents: list[DashboardIncident] = []
    events_by_status: list[DashboardBucket] = []
    tasks_by_status: list[DashboardBucket] = []
    incidents_by_status: list[DashboardBucket] = []
    waste_by_destination: list[DashboardBucket] = []
    carbon_by_category: list[DashboardBucket] = []
    recent_activity: list[dict[str, str | None]] = []


class ClientEventSummary(BaseModel):
    id: UUID
    name: str
    status: EventStatus
    start_date: datetime
    end_date: datetime
    tasks_completion_rate: float = 0
    open_incidents: int = 0
    total_waste_kg: float = 0
    total_carbon_tco2e: float = 0
    report_available: bool = False


class ClientIndicatorByEvent(BaseModel):
    event_id: UUID
    event_name: str
    waste_total_kg: float = 0
    waste_recovery_rate: float = 0
    carbon_tco2e: float = 0
    kgco2e_per_attendee: float = 0
    average_rating: float = 0
    incidents_total: int = 0
    tasks_completion_rate: float = 0


class ClientDashboardResponse(BaseModel):
    client: DashboardClient
    total_events: int = 0
    active_events: int = 0
    finished_events: int = 0
    reports_available: int = 0
    open_incidents: int = 0
    resolved_incidents: int = 0
    total_waste_kg: float = 0
    recovered_waste_kg: float = 0
    recovery_rate: float = 0
    waste_recovery_rate: float = 0
    total_carbon_kgco2e: float = 0
    total_carbon_tco2e: float = 0
    average_satisfaction: float = 0
    latest_events: list[DashboardEvent] = []
    latest_reports: list[DashboardReport] = []
    events_summary: list[ClientEventSummary] = []
    indicators_by_event: list[ClientIndicatorByEvent] = []


class WorkerEventSummary(BaseModel):
    id: UUID
    name: str
    status: EventStatus
    start_date: datetime
    end_date: datetime
    location_name: str | None = None
    pending_tasks: int = 0
    open_incidents: int = 0


class WorkerDashboardResponse(BaseModel):
    assigned_events: int = 0
    pending_tasks: int = 0
    in_progress_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = 0
    assigned_incidents: int = 0
    open_incidents: int = 0
    resolved_incidents: int = 0
    today_tasks: list[DashboardTaskItem] = []
    upcoming_tasks: list[DashboardTaskItem] = []
    assigned_events_list: list[WorkerEventSummary] = []
    recent_incidents: list[DashboardIncident] = []
    upcoming_events: list[DashboardEvent] = []


class EventDashboardResponse(BaseModel):
    event: DashboardEvent
    tasks: dict
    incidents: dict
    waste: dict
    carbon: dict
    survey: dict
    forms: dict = Field(default_factory=dict)
    forms_by_session: list[dict] = Field(default_factory=list)
    evidences: dict
    alerts: dict
    critical_zones: list[DashboardBucket] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
