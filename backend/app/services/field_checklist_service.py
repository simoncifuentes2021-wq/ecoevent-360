from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import can_access_event, can_operate_event
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.core import Event, EventStaff, User
from app.models.enums import UserRole
from app.models.field_checklist import FieldChecklistHistory, FieldChecklistItem
from app.schemas.field_checklist_schema import ChecklistItemCreate, ChecklistItemUpdate
from app.services.field_checklist_email_service import send_overdue_checklist_email

logger = logging.getLogger(__name__)
EDIT_ROLES = {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}
STATUS_LABELS = {
    "PENDING": "Pendiente", "IN_PROGRESS": "En curso",
    "COMPLETED": "Completada", "BLOCKED": "Con problema",
}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _event(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="No se encontró el evento")
    return event


def _can_read_event(db: Session, event_id: UUID, actor: User) -> Event:
    event = _event(db, event_id)
    if actor.role not in EDIT_ROLES or not can_access_event(actor, event_id, db):
        raise HTTPException(status_code=403, detail="No tienes acceso a este evento")
    return event


def _target_user(db: Session, event_id: UUID, actor: User, target_id: UUID | None) -> User:
    user_id = target_id or actor.id
    target = db.get(User, user_id)
    if not target or not target.is_active or target.role not in EDIT_ROLES:
        raise HTTPException(status_code=400, detail="La persona seleccionada no puede usar este checklist")
    if actor.role != UserRole.SUPER_ADMIN and target.id != actor.id:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede editar el checklist de otra persona")
    if target.id != actor.id:
        assigned = db.scalar(select(EventStaff.id).where(
            EventStaff.event_id == event_id, EventStaff.user_id == target.id
        ))
        if not assigned and target.role == UserRole.SUPERVISOR:
            raise HTTPException(status_code=400, detail="La persona no está asignada a este evento")
    return target


def _history(db: Session, item: FieldChecklistItem, actor: User, action: str, description: str) -> None:
    db.add(FieldChecklistHistory(
        event_id=item.event_id, item_id=item.id, actor_id=actor.id,
        action=action, description=description,
    ))


def _read(item: FieldChecklistItem) -> dict:
    return {
        "id": item.id, "event_id": item.event_id, "user_id": item.user_id,
        "title": item.title, "details": item.details, "due_at": item.due_at,
        "status": item.status, "status_note": item.status_note,
        "reminder_sent_at": item.reminder_sent_at, "reminder_attempts": item.reminder_attempts,
        "reminder_failed": item.reminder_sent_at is None and item.reminder_attempts >= 8,
        "created_by": item.created_by, "updated_by": item.updated_by,
        "created_at": item.created_at, "updated_at": item.updated_at,
        "owner_name": item.user.full_name, "owner_email": item.user.email,
    }


def list_people(db: Session, event_id: UUID, actor: User) -> list[dict]:
    _can_read_event(db, event_id, actor)
    if actor.role != UserRole.SUPER_ADMIN:
        return [{"id": actor.id, "full_name": actor.full_name, "email": actor.email}]
    event_people = select(EventStaff.user_id).where(EventStaff.event_id == event_id).union(
        select(FieldChecklistItem.user_id).where(FieldChecklistItem.event_id == event_id)
    )
    users = list(db.scalars(
        select(User).where(
            User.id.in_(event_people), User.is_active.is_(True), User.role.in_(EDIT_ROLES)
        ).order_by(User.full_name)
    ).unique().all())
    if actor.id not in {person.id for person in users}:
        users.insert(0, actor)
    return [{"id": person.id, "full_name": person.full_name, "email": person.email} for person in users]


def email_status() -> dict[str, bool]:
    return {"configured": bool(settings.resend_api_key)}


def list_items(db: Session, event_id: UUID, actor: User, owner_id: UUID | None) -> list[dict]:
    _can_read_event(db, event_id, actor)
    if owner_id and actor.role != UserRole.SUPER_ADMIN and owner_id != actor.id:
        raise HTTPException(status_code=403, detail="No puedes revisar el checklist de otra persona")
    selected_owner = owner_id or actor.id
    query = select(FieldChecklistItem).options(joinedload(FieldChecklistItem.user)).where(
        FieldChecklistItem.event_id == event_id,
        FieldChecklistItem.user_id == selected_owner,
    ).order_by(FieldChecklistItem.due_at, FieldChecklistItem.created_at)
    return [_read(item) for item in db.scalars(query).unique().all()]


def create_item(db: Session, event_id: UUID, payload: ChecklistItemCreate, actor: User) -> dict:
    _can_read_event(db, event_id, actor)
    if actor.role == UserRole.SUPERVISOR and not can_operate_event(actor, event_id, db):
        raise HTTPException(status_code=403, detail="El evento no está disponible para cambios operativos")
    target = _target_user(db, event_id, actor, payload.user_id)
    due_at = payload.due_at
    if due_at.tzinfo is not None:
        due_at = due_at.astimezone(UTC).replace(tzinfo=None)
    item = FieldChecklistItem(
        event_id=event_id, user_id=target.id, title=payload.title.strip(),
        details=payload.details.strip() if payload.details else None,
        due_at=due_at, created_by=actor.id, updated_by=actor.id,
    )
    db.add(item)
    db.flush()
    _history(db, item, actor, "CREATED", "Actividad agregada al checklist personal")
    db.commit()
    db.refresh(item)
    return _read(item)


def update_item(db: Session, item_id: UUID, payload: ChecklistItemUpdate, actor: User) -> dict:
    item = db.scalar(select(FieldChecklistItem).options(joinedload(FieldChecklistItem.user)).where(FieldChecklistItem.id == item_id))
    if not item:
        raise HTTPException(status_code=404, detail="No se encontró la actividad")
    _can_read_event(db, item.event_id, actor)
    if actor.role != UserRole.SUPER_ADMIN and item.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Solo puedes editar tu propio checklist")
    changes = payload.model_dump(exclude_unset=True)
    descriptions: list[str] = []
    for key, value in changes.items():
        if key == "due_at" and value is not None and value.tzinfo is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        if key == "title" and value is not None:
            value = value.strip()
        if key == "details" and value is not None:
            value = value.strip() or None
        if getattr(item, key) != value:
            if key == "due_at" or (key == "status" and value == "PENDING"):
                item.reminder_sent_at = None
                item.reminder_attempted_at = None
                item.reminder_attempts = 0
            setattr(item, key, value)
            if key == "status":
                descriptions.append(f"Cambió el estado a {STATUS_LABELS[value]}")
            else:
                descriptions.append({
                "title": "Cambió el nombre de la actividad",
                "details": "Actualizó las instrucciones",
                "due_at": "Cambió la fecha o la hora programada",
                "status_note": "Actualizó la nota de la actividad",
                }[key])
    if descriptions:
        item.updated_by = actor.id
        item.updated_at = _now()
        _history(db, item, actor, "UPDATED", "; ".join(descriptions))
    db.commit()
    db.refresh(item)
    return _read(item)


def list_history(db: Session, item_id: UUID, actor: User) -> list[dict]:
    item = db.get(FieldChecklistItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="No se encontró la actividad")
    _can_read_event(db, item.event_id, actor)
    if actor.role != UserRole.SUPER_ADMIN and item.user_id != actor.id:
        raise HTTPException(status_code=403, detail="No puedes revisar este historial")
    rows = db.execute(
        select(FieldChecklistHistory, User.full_name)
        .outerjoin(User, User.id == FieldChecklistHistory.actor_id)
        .where(FieldChecklistHistory.item_id == item_id)
        .order_by(FieldChecklistHistory.created_at.desc())
    ).all()
    return [{"id": row.id, "actor_name": name or "Usuario eliminado", "action": row.action,
             "description": row.description, "created_at": row.created_at} for row, name in rows]


def send_due_reminders_once() -> int:
    delivered = 0
    now = _now()
    with SessionLocal() as db:
        candidates = list(db.scalars(
            select(FieldChecklistItem).options(joinedload(FieldChecklistItem.user), joinedload(FieldChecklistItem.event))
            .where(
                FieldChecklistItem.status.in_(["PENDING", "IN_PROGRESS", "BLOCKED"]),
                FieldChecklistItem.due_at <= now,
                FieldChecklistItem.reminder_sent_at.is_(None),
                or_(FieldChecklistItem.reminder_attempted_at.is_(None), FieldChecklistItem.reminder_attempted_at <= now - timedelta(minutes=15)),
                FieldChecklistItem.reminder_attempts < 8,
            )
            .order_by(FieldChecklistItem.due_at).limit(30)
            .with_for_update(of=FieldChecklistItem, skip_locked=True)
        ).unique().all())
        for item in candidates:
            item.reminder_attempted_at = now
            item.reminder_attempts += 1
            db.flush()
            sent = send_overdue_checklist_email(
                recipient=item.user.email, name=item.user.full_name,
                event_name=item.event.name, title=item.title,
                due_at=item.due_at.replace(tzinfo=UTC).astimezone(ZoneInfo("America/Santiago")).strftime("%d-%m-%Y %H:%M"),
            )
            if sent:
                item.reminder_sent_at = _now()
                delivered += 1
            db.commit()
    return delivered


def reminder_worker_loop(stop_event) -> None:
    logger.info("field_checklist_reminder_worker_started")
    while not stop_event.wait(60):
        try:
            send_due_reminders_once()
        except Exception:
            logger.exception("field_checklist_reminder_worker_iteration_failed")
    logger.info("field_checklist_reminder_worker_stopped")
