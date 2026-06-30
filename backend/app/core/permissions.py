from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Event, EventOrder, EventOrderItem, OrderEvidence, EventStaff, Task, User
from app.models.enums import EventStatus, UserRole

CLOSURE_WINDOW_DAYS = 7
OPERATIONAL_ROLES = {UserRole.SUPERVISOR, UserRole.WORKER, UserRole.LOGISTICS_OPERATOR}


def can_access_client(user: User, client_id: UUID, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.CLIENT:
        return user.client_id == client_id
    return False


def _is_assigned_to_event(user: User, event_id: UUID, db: Session) -> bool:
    return db.scalar(
        select(EventStaff.id).where(EventStaff.event_id == event_id, EventStaff.user_id == user.id)
    ) is not None


def _has_task_in_event(user: User, event_id: UUID, db: Session) -> bool:
    return db.scalar(
        select(Task.id).where(Task.event_id == event_id, Task.assigned_to == user.id)
    ) is not None


def _has_operational_relation(user: User, event_id: UUID, db: Session) -> bool:
    return _is_assigned_to_event(user, event_id, db) or _has_task_in_event(user, event_id, db)


def _is_in_closure_window(event: Event) -> bool:
    return datetime.utcnow() <= event.end_date + timedelta(days=CLOSURE_WINDOW_DAYS)


def is_hidden_from_operational_roles(event: Event, user: User) -> bool:
    return user.role in OPERATIONAL_ROLES and event.hidden_from_operations


def can_view_operational_event(user: User, event: Event, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.CLIENT:
        return user.client_id is not None and event.client_id == user.client_id
    if user.role in OPERATIONAL_ROLES:
        if is_hidden_from_operational_roles(event, user):
            return False
        if event.status == EventStatus.QUOTE:
            return False
        return _has_operational_relation(user, event.id, db)
    return False


def can_operate_event(user: User, event_id: UUID, db: Session) -> bool:
    event = db.get(Event, event_id)
    if event is None:
        return False
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR:
        if not can_view_operational_event(user, event, db):
            return False
        return event.status in {EventStatus.PLANNING, EventStatus.IN_PROGRESS} or (
            event.status == EventStatus.FINISHED and _is_in_closure_window(event)
        )
    if user.role == UserRole.WORKER:
        if not can_view_operational_event(user, event, db):
            return False
        return event.status == EventStatus.IN_PROGRESS
    return False


def can_close_assigned_task(user: User, event_id: UUID, db: Session) -> bool:
    event = db.get(Event, event_id)
    if event is None:
        return False
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role in OPERATIONAL_ROLES:
        if not can_view_operational_event(user, event, db):
            return False
        return event.status == EventStatus.IN_PROGRESS or (
            event.status == EventStatus.FINISHED and _is_in_closure_window(event)
        )
    return False


def can_access_event(user: User, event_id: UUID, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True

    event = db.get(Event, event_id)
    if event is None:
        return False

    return can_view_operational_event(user, event, db)


def can_manage_event(user: User, event_id: UUID, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR:
        return can_operate_event(user, event_id, db)
    return False


def is_logistics_operator(user: User) -> bool:
    return user.role == UserRole.LOGISTICS_OPERATOR


def can_create_logistics_order(user: User, event_id: UUID, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR:
        return can_manage_event(user, event_id, db)
    return False


def can_access_logistics_order(user: User, order: EventOrder, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.CLIENT:
        event = db.get(Event, order.event_id)
        return event is not None and user.client_id is not None and event.client_id == user.client_id
    if user.role == UserRole.SUPERVISOR:
        return can_access_event(user, order.event_id, db)
    if is_logistics_operator(user):
        return order.assigned_to == user.id
    return False


def can_manage_logistics_order(user: User, order: EventOrder, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR:
        return can_manage_event(user, order.event_id, db)
    return False


def can_access_order(user: User, order_id: UUID, db: Session) -> bool:
    order = db.get(EventOrder, order_id)
    if order is None:
        return False
    return can_access_logistics_order(user, order, db)


def can_manage_order(user: User, order_id: UUID, db: Session) -> bool:
    order = db.get(EventOrder, order_id)
    if order is None:
        return False
    return can_manage_logistics_order(user, order, db)


def can_complete_order_item_stage(user: User, item_id: UUID, db: Session) -> bool:
    item = db.get(EventOrderItem, item_id)
    if item is None:
        return False
    order = db.get(EventOrder, item.order_id)
    if order is None:
        return False
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR:
        return can_manage_event(user, order.event_id, db)
    if is_logistics_operator(user):
        return order.assigned_to == user.id
    return False


def can_upload_order_evidence(user: User, order_id: UUID, db: Session) -> bool:
    order = db.get(EventOrder, order_id)
    if order is None:
        return False
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR:
        return can_manage_event(user, order.event_id, db)
    if is_logistics_operator(user):
        return order.assigned_to == user.id
    return False


def can_view_order_evidence(user: User, evidence_id: UUID, db: Session) -> bool:
    evidence = db.get(OrderEvidence, evidence_id)
    if evidence is None:
        return False
    if user.role == UserRole.CLIENT and not evidence.visible_to_client:
        return False
    return can_access_order(user, evidence.order_id, db)
