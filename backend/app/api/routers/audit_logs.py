import csv
from datetime import datetime
from io import StringIO
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.core.permissions import can_access_event
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.audit_log_schema import AuditLogListResponse, AuditLogRead
from app.services.audit_log_service import list_audit_logs

router = APIRouter(prefix="/audit-logs", tags=["audit logs"])
event_router = APIRouter(prefix="/events", tags=["audit logs"])


def _to_read(log: AuditLog) -> AuditLogRead:
    return AuditLogRead(
        id=log.id,
        user_id=log.user_id,
        user_name=log.user.full_name if log.user else None,
        user_email=log.user.email if log.user else None,
        user_role=log.user.role.value if log.user else None,
        event_id=log.event_id,
        event_name=log.event.name if log.event else None,
        client_id=log.client_id,
        client_name=log.client.business_name if log.client else None,
        task_id=log.task_id,
        task_title=log.task.title if log.task else None,
        incident_id=log.incident_id,
        incident_title=log.incident.title if log.incident else None,
        zone_id=log.zone_id,
        zone_name=log.zone.name if log.zone else None,
        action=log.action,
        module=log.module,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        status=log.status,
        old_data=log.old_data,
        new_data=log.new_data,
        metadata=log.metadata_,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        request_method=log.request_method,
        request_path=log.request_path,
        description=log.description,
        created_at=log.created_at,
    )


@router.get(
    "",
    response_model=AuditLogListResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def get_audit_logs(
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
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    items, total = list_audit_logs(
        db,
        page=page,
        limit=limit,
        user_id=user_id,
        event_id=event_id,
        client_id=client_id,
        task_id=task_id,
        incident_id=incident_id,
        zone_id=zone_id,
        module=module,
        action=action,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        from_date=from_date,
        to_date=to_date,
        q=q,
    )
    return AuditLogListResponse(
        items=[_to_read(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        pages=ceil(total / limit) if total else 0,
    )


@router.get(
    "/export",
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def export_audit_logs(
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
    db: Session = Depends(get_db),
):
    items, _ = list_audit_logs(
        db,
        page=1,
        limit=10000,
        user_id=user_id,
        event_id=event_id,
        client_id=client_id,
        task_id=task_id,
        incident_id=incident_id,
        zone_id=zone_id,
        module=module,
        action=action,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        from_date=from_date,
        to_date=to_date,
        q=q,
    )
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "created_at",
            "user_name",
            "user_email",
            "user_role",
            "module",
            "action",
            "status",
            "event_name",
            "client_name",
            "zone_name",
            "task_title",
            "incident_title",
            "entity_type",
            "entity_id",
            "description",
            "request_method",
            "request_path",
            "ip_address",
        ]
    )
    for log in items:
        writer.writerow(
            [
                log.created_at.isoformat() if log.created_at else "",
                log.user.full_name if log.user else "",
                log.user.email if log.user else "",
                log.user.role.value if log.user else "",
                log.module,
                log.action,
                log.status,
                log.event.name if log.event else "",
                log.client.business_name if log.client else "",
                log.zone.name if log.zone else "",
                log.task.title if log.task else "",
                log.incident.title if log.incident else "",
                log.entity_type or "",
                str(log.entity_id or ""),
                log.description or "",
                log.request_method or "",
                log.request_path or "",
                log.ip_address or "",
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="audit-logs.csv"'},
    )


@event_router.get("/{event_id}/audit-logs", response_model=AuditLogListResponse)
def get_event_audit_logs(
    event_id: UUID,
    module: str | None = None,
    action: str | None = None,
    status: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    task_id: UUID | None = None,
    incident_id: UUID | None = None,
    zone_id: UUID | None = None,
    user_id: UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AuditLogListResponse:
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if current_user.role == UserRole.SUPERVISOR and not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    items, total = list_audit_logs(
        db,
        page=page,
        limit=limit,
        event_id=event_id,
        module=module,
        action=action,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        task_id=task_id,
        incident_id=incident_id,
        zone_id=zone_id,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
    )
    return AuditLogListResponse(
        items=[_to_read(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        pages=ceil(total / limit) if total else 0,
    )
