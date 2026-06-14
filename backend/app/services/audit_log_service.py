from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from fastapi import Request
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy import func, insert, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.audit_log import AuditLog
from app.models.core import (
    Client,
    Event,
    EventZone,
    Evidence,
    Incident,
    Task,
    User,
    WasteRecord,
)

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "authorization",
    "access_token",
    "refresh_token",
    "token",
    "secret",
    "secrets",
    "password",
    "password_hash",
    "hashed_password",
    "api_key",
}


def sanitize_audit_data(value):
    if value is None:
        return None
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            key_text = str(key)
            if any(sensitive in key_text.lower() for sensitive in SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_audit_data(item)
        return sanitized
    if isinstance(value, list | tuple | set):
        return [sanitize_audit_data(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def serialize_model_for_audit(model, *, include: set[str] | None = None) -> dict | None:
    if model is None:
        return None
    try:
        mapper = sqlalchemy_inspect(model.__class__)
        data = {}
        for column in mapper.columns:
            key = column.key
            if include is not None and key not in include:
                continue
            data[key] = getattr(model, key)
        return sanitize_audit_data(data)
    except Exception:
        logger.exception("Could not serialize model for audit")
        return None


def _value(value):
    if isinstance(value, Enum):
        return value.value
    return value


def _get_text(data: dict | None, *keys: str):
    if not data:
        return None
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return _value(value)
    return None


def _user_name(user: User | None) -> str:
    return user.full_name if user else "Sistema"


def _context_metadata(
    *,
    event: Event | None,
    client: Client | None,
    task: Task | None,
    incident: Incident | None,
    zone: EventZone | None,
    evidence: Evidence | None,
    waste_record: WasteRecord | None,
) -> dict:
    data: dict = {}
    if event:
        data.update(
            {
                "event_id": event.id,
                "event_name": event.name,
                "event_status": event.status,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "estimated_attendees": event.estimated_attendees,
            }
        )
    if client:
        data.update({"client_id": client.id, "client_name": client.business_name})
    if zone:
        data.update({"zone_id": zone.id, "zone_name": zone.name})
    if task:
        data.update(
            {
                "task_id": task.id,
                "task_title": task.title,
                "assigned_to": task.assigned_to,
                "assigned_to_name": task.assignee.full_name if task.assignee else None,
                "priority": task.priority,
                "task_status": task.status,
                "scheduled_at": task.scheduled_at,
                "completed_at": task.completed_at,
            }
        )
    if incident:
        data.update(
            {
                "incident_id": incident.id,
                "incident_title": incident.title,
                "incident_type": incident.incident_type,
                "incident_status": incident.status,
                "priority": incident.priority,
                "assigned_to": incident.assigned_to,
                "assigned_to_name": incident.assignee.full_name if incident.assignee else None,
                "resolved_at": incident.resolved_at,
                "closed_at": incident.closed_at,
            }
        )
    if evidence:
        data.update(
            {
                "evidence_id": evidence.id,
                "task_id": evidence.task_id,
                "incident_id": evidence.incident_id,
                "file_type": evidence.file_type,
                "description": evidence.description,
                "uploaded_by": evidence.uploaded_by,
            }
        )
    if waste_record:
        data.update(
            {
                "waste_record_id": waste_record.id,
                "waste_type_id": waste_record.waste_type_id,
                "waste_type": waste_record.waste_type.name if waste_record.waste_type else None,
                "weight_kg": waste_record.weight_kg,
                "destination": waste_record.destination,
                "recorded_by": waste_record.recorded_by,
                "evidence_id": waste_record.evidence_id,
            }
        )
    return sanitize_audit_data(data) or {}


def build_audit_description(
    action: str,
    module: str,
    *,
    user: User | None = None,
    event: Event | None = None,
    task: Task | None = None,
    incident: Incident | None = None,
    zone: EventZone | None = None,
    old_data: dict | None = None,
    new_data: dict | None = None,
    metadata: dict | None = None,
) -> str:
    actor = _user_name(user)
    event_name = event.name if event else _get_text(metadata, "event_name")
    task_title = task.title if task else _get_text(metadata, "task_title", "title")
    incident_title = incident.title if incident else _get_text(metadata, "incident_title", "title")
    zone_name = zone.name if zone else _get_text(metadata, "zone_name")
    old_status = _get_text(metadata, "old_status") or _get_text(old_data, "status")
    new_status = _get_text(metadata, "new_status") or _get_text(new_data, "status")
    event_part = f" en el evento '{event_name}'" if event_name else ""
    zone_part = f", zona '{zone_name}'" if zone_name else ""

    if module == "tasks":
        if action == "TASK_CREATED" or action == "CREATE":
            return f"{actor} creo la tarea '{task_title or 'sin titulo'}'{event_part}{zone_part}."
        if action == "TASK_STARTED" or (action == "STATUS_CHANGE" and new_status == "IN_PROGRESS"):
            return f"{actor} inicio la tarea '{task_title or 'sin titulo'}'{event_part}{zone_part}."
        if action == "TASK_COMPLETED" or action == "COMPLETE":
            return f"{actor} completo la tarea '{task_title or 'sin titulo'}'{event_part}{zone_part}."
        if action in {"TASK_OBSERVED", "TASK_CANCELLED", "TASK_STATUS_CHANGED", "STATUS_CHANGE"}:
            return (
                f"{actor} cambio el estado de la tarea '{task_title or 'sin titulo'}' "
                f"de {old_status or 'sin estado'} a {new_status or 'sin estado'}."
            )
        if action == "UPDATE":
            return f"{actor} actualizo la tarea '{task_title or 'sin titulo'}'{event_part}{zone_part}."

    if module == "incidents":
        if action == "INCIDENT_CREATED" or action == "CREATE":
            return f"{actor} reporto la incidencia '{incident_title or 'sin titulo'}'{event_part}{zone_part}."
        if action == "INCIDENT_RESOLVED" or action == "RESOLVE":
            return f"{actor} resolvio la incidencia '{incident_title or 'sin titulo'}'{event_part}{zone_part}."
        if action == "INCIDENT_CLOSED" or action == "CLOSE":
            return f"{actor} cerro la incidencia '{incident_title or 'sin titulo'}'{event_part}{zone_part}."
        if action == "UPDATE":
            return f"{actor} actualizo la incidencia '{incident_title or 'sin titulo'}'{event_part}{zone_part}."

    if module == "evidences":
        if action in {"EVIDENCE_UPLOADED", "CREATE"}:
            if task_title:
                return f"{actor} subio una evidencia para la tarea '{task_title}'{event_part}{zone_part}."
            if incident_title:
                return f"{actor} subio una evidencia para la incidencia '{incident_title}'{event_part}{zone_part}."
            return f"{actor} subio una evidencia{event_part}{zone_part}."
        if action in {"EVIDENCE_DELETED", "DELETE"}:
            return f"{actor} elimino una evidencia{event_part}{zone_part}."

    if module == "waste":
        weight = _get_text(metadata, "weight_kg") or _get_text(new_data, "weight_kg")
        waste_type = _get_text(metadata, "waste_type") or _get_text(new_data, "waste_type_id") or "residuo"
        destination = _get_text(metadata, "destination") or _get_text(new_data, "destination")
        if action in {"WASTE_RECORD_CREATED", "CREATE"}:
            detail = f"{weight} kg de {waste_type}" if weight else str(waste_type)
            return f"{actor} registro {detail} con destino {destination or 'sin destino'}{event_part}{zone_part}."
        if action in {"WASTE_RECORD_UPDATED", "UPDATE"}:
            return f"{actor} actualizo un registro de residuos{event_part}{zone_part}."
        if action in {"WASTE_RECORD_DELETED_OR_VOIDED", "DELETE"}:
            return f"{actor} elimino o anulo un registro de residuos{event_part}{zone_part}."

    if module == "events":
        if action == "EVENT_STATUS_CHANGED" or (action == "STATUS_CHANGE" and event_name):
            return (
                f"{actor} cambio el estado del evento '{event_name}' "
                f"de {old_status or 'sin estado'} a {new_status or 'sin estado'}."
            )
        if action == "EVENT_CREATED" or action == "CREATE":
            return f"{actor} creo el evento '{event_name or 'sin nombre'}'."
        if action == "EVENT_UPDATED" or action == "UPDATE":
            return f"{actor} actualizo el evento '{event_name or 'sin nombre'}'."
        if action in {"EVENT_CANCELLED", "DELETE"}:
            return f"{actor} cancelo el evento '{event_name or 'sin nombre'}'."

    if module == "staff":
        assigned_user_name = _get_text(metadata, "assigned_user_name")
        if action in {"STAFF_ASSIGNED", "CREATE"}:
            return f"{actor} asigno a {assigned_user_name or 'personal'} al evento '{event_name or 'sin evento'}'."
        if action in {"STAFF_REMOVED", "DELETE"}:
            return f"{actor} quito a {assigned_user_name or 'personal'} del evento '{event_name or 'sin evento'}'."

    if module == "reports" and action in {"REPORT_GENERATED", "CREATE"}:
        return f"{actor} genero un reporte para el evento '{event_name or 'sin evento'}'."

    return f"{actor} realizo la accion {action} en el modulo {module}."


def _resolve_context(
    db: Session,
    *,
    module: str,
    entity_type: str | None,
    entity_id: UUID | None,
    event_id: UUID | None,
    client_id: UUID | None,
    task_id: UUID | None,
    incident_id: UUID | None,
    zone_id: UUID | None,
) -> tuple[Event | None, Client | None, Task | None, Incident | None, EventZone | None, Evidence | None, WasteRecord | None]:
    normalized_entity = (entity_type or "").lower()
    if not task_id and entity_id and (module == "tasks" or normalized_entity == "task"):
        task_id = entity_id
    if not incident_id and entity_id and (module == "incidents" or normalized_entity == "incident"):
        incident_id = entity_id
    if not zone_id and entity_id and (module == "zones" or normalized_entity in {"eventzone", "zone"}):
        zone_id = entity_id

    task = db.get(Task, task_id) if task_id else None
    incident = db.get(Incident, incident_id) if incident_id else None
    evidence = (
        db.get(Evidence, entity_id)
        if entity_id and (module == "evidences" or normalized_entity == "evidence")
        else None
    )
    waste_record = (
        db.get(WasteRecord, entity_id)
        if entity_id and (module == "waste" or normalized_entity == "wasterecord")
        else None
    )

    if task:
        event_id = event_id or task.event_id
        zone_id = zone_id or task.zone_id
    if incident:
        event_id = event_id or incident.event_id
        zone_id = zone_id or incident.zone_id
    if evidence:
        event_id = event_id or evidence.event_id
        task = task or evidence.task
        incident = incident or evidence.incident
        zone_id = zone_id or (task.zone_id if task else None) or (incident.zone_id if incident else None)
    if waste_record:
        event_id = event_id or waste_record.event_id
        zone_id = zone_id or waste_record.zone_id
    zone = db.get(EventZone, zone_id) if zone_id else None
    if zone:
        event_id = event_id or zone.event_id
    event = db.get(Event, event_id) if event_id else None
    if event:
        client_id = client_id or event.client_id
    client = db.get(Client, client_id) if client_id else None
    return event, client, task, incident, zone, evidence, waste_record


def create_audit_log(
    db: Session,
    *,
    user: User | None = None,
    action: str,
    module: str,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    event_id: UUID | None = None,
    client_id: UUID | None = None,
    task_id: UUID | None = None,
    incident_id: UUID | None = None,
    zone_id: UUID | None = None,
    description: str | None = None,
    status: str = "SUCCESS",
    old_data: dict | None = None,
    new_data: dict | None = None,
    metadata: dict | None = None,
    request: Request | None = None,
) -> AuditLog | None:
    try:
        event, client, task, incident, zone, evidence, waste_record = _resolve_context(
            db,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            event_id=event_id,
            client_id=client_id,
            task_id=task_id,
            incident_id=incident_id,
            zone_id=zone_id,
        )
        merged_metadata = {
            **_context_metadata(
                event=event,
                client=client,
                task=task,
                incident=incident,
                zone=zone,
                evidence=evidence,
                waste_record=waste_record,
            ),
            **(sanitize_audit_data(metadata) or {}),
        }
        if old_data and "status" in old_data:
            merged_metadata.setdefault("old_status", _value(old_data["status"]))
        if new_data and "status" in new_data:
            merged_metadata.setdefault("new_status", _value(new_data["status"]))
        final_description = description or build_audit_description(
            action,
            module,
            user=user,
            event=event,
            task=task,
            incident=incident,
            zone=zone,
            old_data=old_data,
            new_data=new_data,
            metadata=merged_metadata,
        )
        log_values = {
            "user_id": user.id if user else None,
            "event_id": event.id if event else event_id,
            "client_id": client.id if client else client_id,
            "task_id": task.id if task else task_id,
            "incident_id": incident.id if incident else incident_id,
            "zone_id": zone.id if zone else zone_id,
            "action": action,
            "module": module,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": status,
            "old_data": sanitize_audit_data(old_data),
            "new_data": sanitize_audit_data(new_data),
            "metadata": sanitize_audit_data(merged_metadata),
            "description": final_description,
        }
        if request is not None:
            forwarded_for = request.headers.get("x-forwarded-for")
            log_values["ip_address"] = (
                forwarded_for.split(",")[0].strip()
                if forwarded_for
                else request.client.host if request.client else None
            )
            log_values["user_agent"] = request.headers.get("user-agent")
            log_values["request_method"] = request.method
            log_values["request_path"] = str(request.url.path)
        db.execute(insert(AuditLog.__table__).inline().values(**log_values))
        db.commit()
        return None
    except Exception:
        db.rollback()
        logger.exception("Audit log could not be persisted")
        return None


def list_audit_logs(
    db: Session,
    *,
    page: int,
    limit: int,
    user_id: UUID | None = None,
    event_id: UUID | None = None,
    client_id: UUID | None = None,
    task_id: UUID | None = None,
    incident_id: UUID | None = None,
    zone_id: UUID | None = None,
    module: str | None = None,
    action: str | None = None,
    status: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    q: str | None = None,
) -> tuple[list[AuditLog], int]:
    filters = []
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if event_id:
        filters.append(AuditLog.event_id == event_id)
    if client_id:
        filters.append(AuditLog.client_id == client_id)
    if task_id:
        filters.append(AuditLog.task_id == task_id)
    if incident_id:
        filters.append(AuditLog.incident_id == incident_id)
    if zone_id:
        filters.append(AuditLog.zone_id == zone_id)
    if module:
        filters.append(AuditLog.module == module)
    if action:
        filters.append(AuditLog.action == action)
    if status:
        filters.append(AuditLog.status == status)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    if from_date:
        filters.append(AuditLog.created_at >= from_date)
    if to_date:
        filters.append(AuditLog.created_at <= to_date)
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                AuditLog.action.ilike(pattern),
                AuditLog.module.ilike(pattern),
                AuditLog.entity_type.ilike(pattern),
                AuditLog.description.ilike(pattern),
                AuditLog.request_path.ilike(pattern),
                AuditLog.user.has(User.full_name.ilike(pattern)),
                AuditLog.user.has(User.email.ilike(pattern)),
                AuditLog.event.has(Event.name.ilike(pattern)),
                AuditLog.client.has(Client.business_name.ilike(pattern)),
                AuditLog.task.has(Task.title.ilike(pattern)),
                AuditLog.incident.has(Incident.title.ilike(pattern)),
                AuditLog.zone.has(EventZone.name.ilike(pattern)),
            )
        )

    total = db.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
    items = list(
        db.scalars(
            select(AuditLog)
            .options(
                selectinload(AuditLog.user),
                selectinload(AuditLog.event),
                selectinload(AuditLog.client),
                selectinload(AuditLog.task).selectinload(Task.assignee),
                selectinload(AuditLog.incident).selectinload(Incident.assignee),
                selectinload(AuditLog.zone),
            )
            .where(*filters)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total
