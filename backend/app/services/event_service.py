from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import (
    Client,
    Event,
    EventService,
    EventStaff,
    EventZone,
    Service,
    Task,
    User,
)
from app.models.enums import EventStatus, UserRole
from app.schemas.event_schema import (
    EventCreate,
    EventServiceCreate,
    EventServiceUpdate,
    EventOperationalVisibilityUpdate,
    EventStatusUpdate,
    EventUpdate,
)

VALID_STATUS_TRANSITIONS = {
    EventStatus.QUOTE: {EventStatus.PLANNING, EventStatus.CANCELLED},
    EventStatus.PLANNING: {EventStatus.IN_PROGRESS, EventStatus.FINISHED, EventStatus.CANCELLED},
    EventStatus.IN_PROGRESS: {EventStatus.FINISHED, EventStatus.CANCELLED},
    EventStatus.FINISHED: {EventStatus.REPORT_DELIVERED},
}
TERMINAL_STATUSES = {EventStatus.REPORT_DELIVERED, EventStatus.CANCELLED}
CRITICAL_EVENT_FIELDS = {
    "client_id",
    "start_date",
    "end_date",
    "estimated_attendees",
    "real_attendees",
}


def get_event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def ensure_can_access_event(db: Session, user: User, event_id: UUID) -> Event:
    event = get_event_or_404(db, event_id)
    if not can_access_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return event


def ensure_can_manage_event(db: Session, user: User, event_id: UUID) -> Event:
    event = get_event_or_404(db, event_id)
    if not can_manage_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return event


def _validate_client(db: Session, client_id: UUID) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if not client.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client is inactive")
    return client


def _validate_event_dates(start_date: datetime, end_date: datetime) -> None:
    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )


def _validate_status_transition(
    current_status: EventStatus, new_status: EventStatus, current_user: User
) -> None:
    if new_status == current_status:
        return

    if current_status in TERMINAL_STATUSES:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can revert terminal events",
            )
    elif new_status not in VALID_STATUS_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {current_status} to {new_status}",
        )


def _event_visibility_filters(user: User):
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return []
    if user.role == UserRole.CLIENT:
        if not user.client_id:
            return [Event.id.is_(None)]
        return [Event.client_id == user.client_id]
    if user.role == UserRole.SUPERVISOR:
        staff_events = select(EventStaff.event_id).where(EventStaff.user_id == user.id)
        return [
            Event.id.in_(staff_events),
            Event.hidden_from_operations.is_(False),
            Event.status != EventStatus.QUOTE,
        ]
    if user.role == UserRole.WORKER:
        staff_events = select(EventStaff.event_id).where(EventStaff.user_id == user.id)
        task_events = select(Task.event_id).where(Task.assigned_to == user.id)
        return [
            or_(Event.id.in_(staff_events), Event.id.in_(task_events)),
            Event.hidden_from_operations.is_(False),
            Event.status != EventStatus.QUOTE,
        ]
    return [Event.id.is_(None)]


def create_event(db: Session, payload: EventCreate, current_user: User) -> Event:
    _validate_client(db, payload.client_id)
    data = payload.model_dump(exclude_unset=True)
    data["created_by"] = current_user.id
    if data.get("status") is None:
        data.pop("status", None)
    event = Event(**data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(
    db: Session,
    *,
    current_user: User,
    q: str | None,
    status_filter: EventStatus | None,
    client_id: UUID | None,
    page: int,
    limit: int,
) -> tuple[list[Event], int]:
    filters = _event_visibility_filters(current_user)
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                Event.name.ilike(pattern),
                Event.event_type.ilike(pattern),
                Event.location_name.ilike(pattern),
                Event.city.ilike(pattern),
            )
        )
    if status_filter is not None:
        filters.append(Event.status == status_filter)
    if client_id is not None:
        filters.append(Event.client_id == client_id)

    total = db.scalar(select(func.count()).select_from(Event).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Event)
            .where(*filters)
            .order_by(Event.start_date.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def get_event_detail(db: Session, event_id: UUID, current_user: User) -> tuple[Event, int, int]:
    ensure_can_access_event(db, current_user, event_id)
    event = db.scalar(
        select(Event).options(selectinload(Event.client)).where(Event.id == event_id)
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    services_count = (
        db.scalar(
            select(func.count()).select_from(EventService).where(EventService.event_id == event_id)
        )
        or 0
    )
    zones_count = (
        db.scalar(select(func.count()).select_from(EventZone).where(EventZone.event_id == event_id))
        or 0
    )
    return event, services_count, zones_count


def update_event(db: Session, event_id: UUID, payload: EventUpdate, current_user: User) -> Event:
    event = ensure_can_manage_event(db, current_user, event_id)
    data = payload.model_dump(exclude_unset=True)

    if not data:
        return event
    if event.status in {EventStatus.FINISHED, EventStatus.REPORT_DELIVERED}:
        critical_updates = CRITICAL_EVENT_FIELDS.intersection(data)
        if critical_updates and current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can edit critical fields on finished events",
            )
    if "client_id" in data:
        _validate_client(db, data["client_id"])
    if data.get("status") is None:
        data.pop("status", None)
    if "status" in data:
        _validate_status_transition(event.status, data["status"], current_user)

    start_date = data.get("start_date", event.start_date)
    end_date = data.get("end_date", event.end_date)
    _validate_event_dates(start_date, end_date)

    for field, value in data.items():
        setattr(event, field, value)
    event.updated_at = datetime.utcnow()
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_event_status(
    db: Session, event_id: UUID, payload: EventStatusUpdate, current_user: User
) -> Event:
    event = ensure_can_manage_event(db, current_user, event_id)
    new_status = payload.status
    if new_status == event.status:
        return event

    _validate_status_transition(event.status, new_status, current_user)

    event.status = new_status
    event.updated_at = datetime.utcnow()
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_operational_visibility(
    db: Session,
    event_id: UUID,
    payload: EventOperationalVisibilityUpdate,
    current_user: User,
) -> Event:
    event = ensure_can_manage_event(db, current_user, event_id)
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    event.hidden_from_operations = payload.hidden_from_operations
    event.updated_at = datetime.utcnow()
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def cancel_event(db: Session, event_id: UUID, current_user: User) -> Event:
    event = ensure_can_manage_event(db, current_user, event_id)
    event.status = EventStatus.CANCELLED
    event.updated_at = datetime.utcnow()
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def add_event_service(
    db: Session, event_id: UUID, payload: EventServiceCreate, current_user: User
) -> EventService:
    ensure_can_manage_event(db, current_user, event_id)
    service = db.get(Service, payload.service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    if not service.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Service is inactive")

    unit_price = payload.unit_price if payload.unit_price is not None else service.base_price
    if unit_price is None:
        unit_price = Decimal("0")
    total_price = payload.quantity * unit_price
    event_service = EventService(
        event_id=event_id,
        service_id=payload.service_id,
        quantity=payload.quantity,
        unit_price=unit_price,
        total_price=total_price,
        notes=payload.notes,
    )
    db.add(event_service)
    db.commit()
    db.refresh(event_service)
    return event_service


def list_event_services(db: Session, event_id: UUID, current_user: User) -> list[EventService]:
    ensure_can_access_event(db, current_user, event_id)
    return list(
        db.scalars(
            select(EventService)
            .where(EventService.event_id == event_id)
            .order_by(EventService.created_at.desc())
        ).all()
    )


def get_event_service_or_404(
    db: Session, event_id: UUID, event_service_id: UUID
) -> EventService:
    event_service = db.get(EventService, event_service_id)
    if not event_service or event_service.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event service not found")
    return event_service


def update_event_service(
    db: Session,
    event_id: UUID,
    event_service_id: UUID,
    payload: EventServiceUpdate,
    current_user: User,
) -> EventService:
    ensure_can_manage_event(db, current_user, event_id)
    event_service = get_event_service_or_404(db, event_id, event_service_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(event_service, field, value)
    quantity = event_service.quantity or Decimal("0")
    unit_price = event_service.unit_price or Decimal("0")
    event_service.total_price = quantity * unit_price
    db.add(event_service)
    db.commit()
    db.refresh(event_service)
    return event_service


def delete_event_service(
    db: Session, event_id: UUID, event_service_id: UUID, current_user: User
) -> None:
    event = ensure_can_manage_event(db, current_user, event_id)
    if event.status in {EventStatus.FINISHED, EventStatus.REPORT_DELIVERED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete services from finished or delivered events",
        )
    event_service = get_event_service_or_404(db, event_id, event_service_id)
    db.delete(event_service)
    db.commit()
