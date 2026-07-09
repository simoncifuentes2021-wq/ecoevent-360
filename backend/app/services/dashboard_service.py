from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, inspect, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event
from app.models.core import (
    Alert,
    CarbonFactor,
    CarbonRecord,
    Client,
    Event,
    EventForm,
    EventStaff,
    EventZone,
    Evidence,
    FormResponse,
    Incident,
    Report,
    SurveyResponse,
    Task,
    User,
    WasteRecord,
    WasteType,
)
from app.models.enums import (
    EventFormStatus,
    EventStatus,
    IncidentStatus,
    PriorityLevel,
    ReportStatus,
    TaskStatus,
    UserRole,
    WasteDestination,
)

ACTIVE_EVENT_STATUSES = {EventStatus.PLANNING, EventStatus.IN_PROGRESS}
FINISHED_EVENT_STATUSES = {EventStatus.FINISHED, EventStatus.REPORT_DELIVERED}
OPEN_INCIDENT_STATUSES = {
    IncidentStatus.REPORTED,
    IncidentStatus.ASSIGNED,
    IncidentStatus.IN_PROGRESS,
}
RESOLVED_INCIDENT_STATUSES = {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}
RECOVERED_WASTE_DESTINATIONS = {
    WasteDestination.RECYCLING,
    WasteDestination.COMPOSTING,
    WasteDestination.RECOVERY,
}


def _float(value: object) -> float:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _round(value: float) -> float:
    return round(value, 2)


def _rate(part: float, total: float) -> float:
    if total <= 0:
        return 0
    return _round((part / total) * 100)


def _count(db: Session, model: type, *filters) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*filters)) or 0)


def _table_exists(db: Session, table_name: str) -> bool:
    return inspect(db.get_bind()).has_table(table_name)


def _sum(db: Session, column, *filters) -> float:
    return _float(db.scalar(select(func.coalesce(func.sum(column), 0)).where(*filters)))


def _bucket_rows(db: Session, label_column, value_column, *filters) -> list[dict[str, float]]:
    rows = db.execute(
        select(label_column, func.coalesce(func.sum(value_column), 0))
        .where(*filters)
        .group_by(label_column)
        .order_by(label_column)
    ).all()
    return [{"name": str(label.value if hasattr(label, "value") else label), "value": _float(value)} for label, value in rows]


def _count_buckets(db: Session, column, *filters) -> list[dict[str, float]]:
    rows = db.execute(
        select(column, func.count()).where(*filters).group_by(column).order_by(column)
    ).all()
    return [{"name": str(label.value if hasattr(label, "value") else label), "value": _float(value)} for label, value in rows]


def _event_waste_by_type(db: Session, event_id: UUID) -> list[dict[str, float]]:
    rows = db.execute(
        select(func.coalesce(WasteType.name, "Sin tipo"), func.coalesce(func.sum(WasteRecord.weight_kg), 0))
        .select_from(WasteRecord)
        .outerjoin(WasteType, WasteType.id == WasteRecord.waste_type_id)
        .where(WasteRecord.event_id == event_id)
        .group_by(WasteType.name)
        .order_by(WasteType.name)
    ).all()
    return [{"name": str(name), "value": _float(value)} for name, value in rows]


def _event_waste_by_zone(db: Session, event_id: UUID) -> list[dict[str, float]]:
    rows = db.execute(
        select(func.coalesce(EventZone.name, "Sin zona"), func.coalesce(func.sum(WasteRecord.weight_kg), 0))
        .select_from(WasteRecord)
        .outerjoin(EventZone, EventZone.id == WasteRecord.zone_id)
        .where(WasteRecord.event_id == event_id)
        .group_by(EventZone.name)
        .order_by(EventZone.name)
    ).all()
    return [{"name": str(name), "value": _float(value)} for name, value in rows]


def _event_carbon_by_scope(db: Session, event_id: UUID) -> list[dict[str, float]]:
    rows = db.execute(
        select(CarbonFactor.scope, func.coalesce(func.sum(CarbonRecord.emissions_kgco2e), 0))
        .select_from(CarbonRecord)
        .join(CarbonFactor, CarbonFactor.id == CarbonRecord.factor_id)
        .where(CarbonRecord.event_id == event_id)
        .group_by(CarbonFactor.scope)
        .order_by(CarbonFactor.scope)
    ).all()
    return [
        {"name": str(scope.value if hasattr(scope, "value") else scope or "Sin scope"), "value": _float(value)}
        for scope, value in rows
    ]


def _event_survey_by_zone(db: Session, event_id: UUID) -> list[dict[str, float]]:
    rows = db.execute(
        select(func.coalesce(EventZone.name, "Sin zona"), func.count())
        .select_from(SurveyResponse)
        .outerjoin(EventZone, EventZone.id == SurveyResponse.zone_id)
        .where(SurveyResponse.event_id == event_id)
        .group_by(EventZone.name)
        .order_by(EventZone.name)
    ).all()
    return [{"name": str(name), "value": _float(value)} for name, value in rows]


def _event_dict(event: Event, client_name: str | None = None) -> dict:
    return {
        "id": event.id,
        "client_id": event.client_id,
        "name": event.name,
        "event_type": event.event_type,
        "client_name": client_name or (event.client.business_name if event.client else None),
        "status": event.status,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "estimated_attendees": event.estimated_attendees,
        "real_attendees": event.real_attendees,
        "location_name": event.location_name,
        "hidden_from_operations": event.hidden_from_operations,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }


def _incident_dict(incident: Incident) -> dict:
    return {
        "id": incident.id,
        "event_id": incident.event_id,
        "event_name": incident.event.name if incident.event else None,
        "zone_name": incident.zone.name if incident.zone else None,
        "title": incident.title,
        "priority": incident.priority,
        "status": incident.status,
        "created_at": incident.created_at,
    }


def _task_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "event_id": task.event_id,
        "event_name": task.event.name if task.event else None,
        "zone_name": task.zone.name if task.zone else None,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "scheduled_at": task.scheduled_at,
    }


def _event_ids_for_user(db: Session, user: User) -> list[UUID]:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return list(db.scalars(select(Event.id)).all())
    if user.role == UserRole.CLIENT:
        if not user.client_id:
            return []
        return list(db.scalars(select(Event.id).where(Event.client_id == user.client_id)).all())
    staff_events = select(EventStaff.event_id).where(EventStaff.user_id == user.id)
    if user.role == UserRole.SUPERVISOR:
        return list(
            db.scalars(
                select(Event.id).where(
                    Event.id.in_(staff_events),
                    Event.hidden_from_operations.is_(False),
                    Event.status != EventStatus.QUOTE,
                )
            ).all()
        )
    task_events = select(Task.event_id).where(Task.assigned_to == user.id)
    return list(
        db.scalars(
            select(Event.id).where(
                or_(Event.id.in_(staff_events), Event.id.in_(task_events)),
                Event.hidden_from_operations.is_(False),
                Event.status != EventStatus.QUOTE,
            )
        ).all()
    )


def _task_completion_rate(db: Session, event_id: UUID) -> float:
    total = _count(db, Task, Task.event_id == event_id)
    completed = _count(db, Task, Task.event_id == event_id, Task.status == TaskStatus.COMPLETED)
    return _rate(completed, total)


def _event_waste(db: Session, event_id: UUID) -> tuple[float, float, float]:
    total = _sum(db, WasteRecord.weight_kg, WasteRecord.event_id == event_id)
    recovered = _sum(
        db,
        WasteRecord.weight_kg,
        WasteRecord.event_id == event_id,
        WasteRecord.destination.in_(RECOVERED_WASTE_DESTINATIONS),
    )
    return total, recovered, _rate(recovered, total)


def _event_carbon(db: Session, event_id: UUID) -> float:
    return _sum(db, CarbonRecord.emissions_kgco2e, CarbonRecord.event_id == event_id)


def get_admin_dashboard(db: Session) -> dict:
    total_tasks = _count(db, Task)
    completed_tasks = _count(db, Task, Task.status == TaskStatus.COMPLETED)
    total_waste = _sum(db, WasteRecord.weight_kg)
    recovered_waste = _sum(db, WasteRecord.weight_kg, WasteRecord.destination.in_(RECOVERED_WASTE_DESTINATIONS))
    total_carbon = _sum(db, CarbonRecord.emissions_kgco2e)
    latest_events = list(
        db.scalars(select(Event).order_by(Event.start_date.desc()).limit(5)).all()
    )
    latest_incidents = list(
        db.scalars(select(Incident).order_by(Incident.created_at.desc()).limit(5)).all()
    )

    return {
        "total_clients": _count(db, Client),
        "total_users": _count(db, User),
        "total_events": _count(db, Event),
        "active_events": _count(db, Event, Event.status.in_(ACTIVE_EVENT_STATUSES)),
        "finished_events": _count(db, Event, Event.status.in_(FINISHED_EVENT_STATUSES)),
        "cancelled_events": _count(db, Event, Event.status == EventStatus.CANCELLED),
        "open_incidents": _count(db, Incident, Incident.status.in_(OPEN_INCIDENT_STATUSES)),
        "resolved_incidents": _count(db, Incident, Incident.status.in_(RESOLVED_INCIDENT_STATUSES)),
        "pending_tasks": _count(db, Task, Task.status == TaskStatus.PENDING),
        "completed_tasks": completed_tasks,
        "completed_tasks_rate": _rate(completed_tasks, total_tasks),
        "total_waste_kg": _round(total_waste),
        "recovered_waste_kg": _round(recovered_waste),
        "waste_recovery_rate": _rate(recovered_waste, total_waste),
        "total_carbon_kgco2e": _round(total_carbon),
        "total_carbon_tco2e": _round(total_carbon / 1000),
        "latest_events": [_event_dict(event) for event in latest_events],
        "latest_incidents": [_incident_dict(incident) for incident in latest_incidents],
        "events_by_status": _count_buckets(db, Event.status),
        "tasks_by_status": _count_buckets(db, Task.status),
        "incidents_by_status": _count_buckets(db, Incident.status),
        "waste_by_destination": _bucket_rows(db, WasteRecord.destination, WasteRecord.weight_kg),
        "carbon_by_category": _bucket_rows(db, CarbonRecord.category, CarbonRecord.emissions_kgco2e),
        "recent_activity": [
            {
                "title": incident.title,
                "description": incident.event.name if incident.event else None,
                "created_at": incident.created_at.isoformat(),
            }
            for incident in latest_incidents
        ],
    }


def get_client_dashboard(db: Session, user: User) -> dict:
    if not user.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CLIENT user does not have an associated client_id",
        )
    client = db.get(Client, user.client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    event_ids = list(db.scalars(select(Event.id).where(Event.client_id == user.client_id)).all())
    events = list(
        db.scalars(
            select(Event)
            .where(Event.client_id == user.client_id)
            .order_by(Event.start_date.desc())
            .limit(5)
        ).all()
    )
    if not event_ids:
        return {
            "client": {"id": client.id, "business_name": client.business_name},
            "latest_events": [],
            "latest_reports": [],
            "events_summary": [],
            "indicators_by_event": [],
        }

    total_waste = _sum(db, WasteRecord.weight_kg, WasteRecord.event_id.in_(event_ids))
    recovered_waste = _sum(
        db,
        WasteRecord.weight_kg,
        WasteRecord.event_id.in_(event_ids),
        WasteRecord.destination.in_(RECOVERED_WASTE_DESTINATIONS),
    )
    total_carbon = _sum(db, CarbonRecord.emissions_kgco2e, CarbonRecord.event_id.in_(event_ids))
    latest_reports = list(
        db.scalars(
            select(Report)
            .where(Report.event_id.in_(event_ids), Report.status.in_({ReportStatus.GENERATED, ReportStatus.DELIVERED}))
            .order_by(Report.created_at.desc())
            .limit(5)
        ).all()
    )
    all_events = list(
        db.scalars(select(Event).where(Event.id.in_(event_ids)).order_by(Event.start_date.desc())).all()
    )

    summaries = []
    indicators = []
    for event in all_events:
        waste_total, waste_recovered, waste_rate = _event_waste(db, event.id)
        carbon_kg = _event_carbon(db, event.id)
        attendees = event.real_attendees or event.estimated_attendees or 0
        average_rating = _float(
            db.scalar(select(func.avg(SurveyResponse.general_rating)).where(SurveyResponse.event_id == event.id))
        )
        incidents_total = _count(db, Incident, Incident.event_id == event.id)
        completion_rate = _task_completion_rate(db, event.id)
        report_available = _count(
            db,
            Report,
            Report.event_id == event.id,
            Report.status.in_({ReportStatus.GENERATED, ReportStatus.DELIVERED}),
        ) > 0
        summaries.append(
            {
                "id": event.id,
                "name": event.name,
                "status": event.status,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "tasks_completion_rate": completion_rate,
                "open_incidents": _count(db, Incident, Incident.event_id == event.id, Incident.status.in_(OPEN_INCIDENT_STATUSES)),
                "total_waste_kg": _round(waste_total),
                "total_carbon_tco2e": _round(carbon_kg / 1000),
                "report_available": report_available,
            }
        )
        indicators.append(
            {
                "event_id": event.id,
                "event_name": event.name,
                "waste_total_kg": _round(waste_total),
                "waste_recovery_rate": waste_rate,
                "carbon_tco2e": _round(carbon_kg / 1000),
                "kgco2e_per_attendee": _round(carbon_kg / attendees) if attendees else 0,
                "average_rating": _round(average_rating),
                "incidents_total": incidents_total,
                "tasks_completion_rate": completion_rate,
            }
        )

    average_satisfaction = _float(
        db.scalar(select(func.avg(SurveyResponse.general_rating)).where(SurveyResponse.event_id.in_(event_ids)))
    )
    return {
        "client": {"id": client.id, "business_name": client.business_name},
        "total_events": len(event_ids),
        "active_events": _count(db, Event, Event.id.in_(event_ids), Event.status.in_(ACTIVE_EVENT_STATUSES)),
        "finished_events": _count(db, Event, Event.id.in_(event_ids), Event.status.in_(FINISHED_EVENT_STATUSES)),
        "reports_available": _count(db, Report, Report.event_id.in_(event_ids), Report.status.in_({ReportStatus.GENERATED, ReportStatus.DELIVERED})),
        "open_incidents": _count(db, Incident, Incident.event_id.in_(event_ids), Incident.status.in_(OPEN_INCIDENT_STATUSES)),
        "resolved_incidents": _count(db, Incident, Incident.event_id.in_(event_ids), Incident.status.in_(RESOLVED_INCIDENT_STATUSES)),
        "total_waste_kg": _round(total_waste),
        "recovered_waste_kg": _round(recovered_waste),
        "recovery_rate": _rate(recovered_waste, total_waste),
        "waste_recovery_rate": _rate(recovered_waste, total_waste),
        "total_carbon_kgco2e": _round(total_carbon),
        "total_carbon_tco2e": _round(total_carbon / 1000),
        "average_satisfaction": _round(average_satisfaction),
        "latest_events": [_event_dict(event, client.business_name) for event in events],
        "latest_reports": [
            {
                "id": report.id,
                "event_id": report.event_id,
                "event_name": report.event.name if report.event else None,
                "title": report.title,
                "status": report.status,
                "pdf_url": report.pdf_url,
                "generated_at": report.generated_at,
                "delivered_at": report.delivered_at,
                "created_at": report.created_at,
            }
            for report in latest_reports
        ],
        "events_summary": summaries,
        "indicators_by_event": indicators,
    }


def get_worker_dashboard(db: Session, user: User) -> dict:
    event_ids = _event_ids_for_user(db, user)
    if not event_ids:
        return {}

    task_filters = [Task.event_id.in_(event_ids)] if user.role == UserRole.SUPERVISOR else [Task.assigned_to == user.id]
    incident_filters = (
        [Incident.event_id.in_(event_ids)]
        if user.role == UserRole.SUPERVISOR
        else [or_(Incident.assigned_to == user.id, Incident.reported_by == user.id)]
    )
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    today_end = datetime.combine(datetime.utcnow().date(), time.max)
    now = datetime.utcnow()
    today_tasks = list(
        db.scalars(
            select(Task)
            .where(*task_filters, Task.scheduled_at >= today_start, Task.scheduled_at <= today_end)
            .order_by(Task.scheduled_at.asc())
            .limit(8)
        ).all()
    )
    upcoming_tasks = list(
        db.scalars(
            select(Task)
            .where(*task_filters, or_(Task.scheduled_at.is_(None), Task.scheduled_at > today_end), Task.status != TaskStatus.COMPLETED)
            .order_by(Task.scheduled_at.asc().nulls_last(), Task.created_at.desc())
            .limit(8)
        ).all()
    )
    events = list(
        db.scalars(select(Event).where(Event.id.in_(event_ids)).order_by(Event.start_date.asc()).limit(8)).all()
    )
    recent_incidents = list(
        db.scalars(
            select(Incident)
            .where(*incident_filters)
            .order_by(Incident.created_at.desc())
            .limit(8)
        ).all()
    )

    assigned_events_list = []
    for event in events:
        assigned_events_list.append(
            {
                "id": event.id,
                "name": event.name,
                "status": event.status,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "location_name": event.location_name,
                "pending_tasks": _count(db, Task, Task.event_id == event.id, Task.status != TaskStatus.COMPLETED),
                "open_incidents": _count(db, Incident, Incident.event_id == event.id, Incident.status.in_(OPEN_INCIDENT_STATUSES)),
            }
        )

    return {
        "assigned_events": len(event_ids),
        "pending_tasks": _count(db, Task, *task_filters, Task.status == TaskStatus.PENDING),
        "in_progress_tasks": _count(db, Task, *task_filters, Task.status == TaskStatus.IN_PROGRESS),
        "completed_tasks": _count(db, Task, *task_filters, Task.status == TaskStatus.COMPLETED),
        "overdue_tasks": _count(db, Task, *task_filters, Task.scheduled_at < now, Task.status.not_in({TaskStatus.COMPLETED, TaskStatus.CANCELLED})),
        "assigned_incidents": _count(db, Incident, *incident_filters),
        "open_incidents": _count(db, Incident, *incident_filters, Incident.status.in_(OPEN_INCIDENT_STATUSES)),
        "resolved_incidents": _count(db, Incident, *incident_filters, Incident.status.in_(RESOLVED_INCIDENT_STATUSES)),
        "today_tasks": [_task_dict(task) for task in today_tasks],
        "upcoming_tasks": [_task_dict(task) for task in upcoming_tasks],
        "assigned_events_list": assigned_events_list,
        "recent_incidents": [_incident_dict(incident) for incident in recent_incidents],
        "upcoming_events": [_event_dict(event) for event in events],
    }


def get_event_dashboard(db: Session, event_id: UUID, user: User, session_id: UUID | None = None) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if not can_access_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    session_filter = [FormResponse.session_id == session_id] if session_id else []
    form_filter = [EventForm.session_id == session_id] if session_id else []
    total_tasks = _count(db, Task, Task.event_id == event_id)
    completed_tasks = _count(db, Task, Task.event_id == event_id, Task.status == TaskStatus.COMPLETED)
    total_waste, recovered_waste, waste_rate = _event_waste(db, event_id)
    total_carbon = _event_carbon(db, event_id)
    attendees = event.real_attendees or event.estimated_attendees or 0
    total_responses = _count(db, SurveyResponse, SurveyResponse.event_id == event_id)
    recommend = _count(db, SurveyResponse, SurveyResponse.event_id == event_id, SurveyResponse.would_recommend.is_(True))
    average_rating = _float(
        db.scalar(select(func.avg(SurveyResponse.general_rating)).where(SurveyResponse.event_id == event_id))
    )
    cleaning_average = _float(
        db.scalar(select(func.avg(SurveyResponse.cleanliness_rating)).where(SurveyResponse.event_id == event_id))
    )
    bathroom_average = _float(
        db.scalar(select(func.avg(SurveyResponse.bathroom_rating)).where(SurveyResponse.event_id == event_id))
    )
    if _table_exists(db, "event_forms") and _table_exists(db, "form_responses"):
        total_forms = _count(db, EventForm, EventForm.event_id == event_id, *form_filter, EventForm.status != EventFormStatus.ARCHIVED)
        active_forms = _count(db, EventForm, EventForm.event_id == event_id, *form_filter, EventForm.status == EventFormStatus.ACTIVE)
        total_form_responses = _count(db, FormResponse, FormResponse.event_id == event_id, *session_filter)
        forms_summary = [
            {"id": form_id, "title": title, "responses": _float(count)}
            for form_id, title, count in db.execute(
                select(EventForm.id, EventForm.title, func.count(FormResponse.id))
                .select_from(EventForm)
                .outerjoin(FormResponse, FormResponse.form_id == EventForm.id)
                .where(EventForm.event_id == event_id, *form_filter, EventForm.status != EventFormStatus.ARCHIVED)
                .group_by(EventForm.id, EventForm.title)
                .order_by(EventForm.created_at.desc())
            ).all()
        ]
    else:
        total_forms = 0
        active_forms = 0
        total_form_responses = 0
        forms_summary = []
    recent_evidences = list(
        db.scalars(select(Evidence).where(Evidence.event_id == event_id).order_by(Evidence.created_at.desc()).limit(5)).all()
    )
    recent_alerts = list(
        db.scalars(select(Alert).where(Alert.event_id == event_id).order_by(Alert.created_at.desc()).limit(5)).all()
    )

    return {
        "event": _event_dict(event),
        "tasks": {
            "total": total_tasks,
            "pending": _count(db, Task, Task.event_id == event_id, Task.status == TaskStatus.PENDING),
            "in_progress": _count(db, Task, Task.event_id == event_id, Task.status == TaskStatus.IN_PROGRESS),
            "completed": completed_tasks,
            "observed": _count(db, Task, Task.event_id == event_id, Task.status == TaskStatus.OBSERVED),
            "cancelled": _count(db, Task, Task.event_id == event_id, Task.status == TaskStatus.CANCELLED),
            "completion_rate": _rate(completed_tasks, total_tasks),
            "by_status": _count_buckets(db, Task.status, Task.event_id == event_id),
        },
        "incidents": {
            "total": _count(db, Incident, Incident.event_id == event_id),
            "open": _count(db, Incident, Incident.event_id == event_id, Incident.status.in_(OPEN_INCIDENT_STATUSES)),
            "resolved": _count(db, Incident, Incident.event_id == event_id, Incident.status == IncidentStatus.RESOLVED),
            "closed": _count(db, Incident, Incident.event_id == event_id, Incident.status == IncidentStatus.CLOSED),
            "critical": _count(db, Incident, Incident.event_id == event_id, Incident.priority == PriorityLevel.CRITICAL),
            "by_status": _count_buckets(db, Incident.status, Incident.event_id == event_id),
            "by_priority": _count_buckets(db, Incident.priority, Incident.event_id == event_id),
        },
        "waste": {
            "total_kg": _round(total_waste),
            "recovered_kg": _round(recovered_waste),
            "landfill_kg": _round(_sum(db, WasteRecord.weight_kg, WasteRecord.event_id == event_id, WasteRecord.destination == WasteDestination.LANDFILL)),
            "recovery_rate": waste_rate,
            "by_type": _event_waste_by_type(db, event_id),
            "by_destination": _bucket_rows(db, WasteRecord.destination, WasteRecord.weight_kg, WasteRecord.event_id == event_id),
            "by_zone": _event_waste_by_zone(db, event_id),
        },
        "carbon": {
            "total_kgco2e": _round(total_carbon),
            "total_tco2e": _round(total_carbon / 1000),
            "kgco2e_per_attendee": _round(total_carbon / attendees) if attendees else 0,
            "by_category": _bucket_rows(db, CarbonRecord.category, CarbonRecord.emissions_kgco2e, CarbonRecord.event_id == event_id),
            "by_scope": _event_carbon_by_scope(db, event_id),
        },
        "survey": {
            "total_responses": total_responses,
            "average_rating": _round(average_rating),
            "recommendation_rate": _rate(recommend, total_responses),
            "cleaning_average": _round(cleaning_average),
            "bathroom_average": _round(bathroom_average),
            "main_problems": _count_buckets(db, SurveyResponse.main_problem, SurveyResponse.event_id == event_id),
            "responses_by_zone": _event_survey_by_zone(db, event_id),
            "main_problem": "Sin dato",
        },
        "forms": {
            "total_forms": total_forms,
            "active_forms": active_forms,
            "total_form_responses": total_form_responses,
            "forms_summary": forms_summary,
        },
        "evidences": {
            "total": _count(db, Evidence, Evidence.event_id == event_id),
            "recent": [
                {
                    "id": evidence.id,
                    "description": evidence.description,
                    "file_url": evidence.file_url,
                    "file_type": evidence.file_type,
                    "created_at": evidence.created_at,
                }
                for evidence in recent_evidences
            ],
        },
        "alerts": {
            "open": _count(db, Alert, Alert.event_id == event_id, Alert.status.in_({"OPEN", "REPORTED", "ASSIGNED", "IN_PROGRESS"})),
            "critical": _count(db, Alert, Alert.event_id == event_id, Alert.priority == PriorityLevel.CRITICAL),
            "recent": [
                {
                    "id": alert.id,
                    "title": alert.title,
                    "priority": alert.priority,
                    "status": alert.status,
                    "created_at": alert.created_at,
                }
                for alert in recent_alerts
            ],
        },
        "critical_zones": [],
        "recommendations": [],
    }
