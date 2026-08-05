from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.event_session_staff_schema import (
    EventSessionStaffCreate,
    EventSessionStaffListResponse,
    EventSessionStaffRead,
    EventSessionStaffUpdate,
    ShowOperationalSummary,
)
from app.services import event_session_staff_service as service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(tags=["show operations"])


def _audit(db, request, current, action, item, old_data=None):
    create_audit_log(
        db, user=current, action=action, module="event_session_staff",
        entity_type="EventSessionStaff", entity_id=item.id, event_id=item.event_id,
        old_data=old_data, new_data=serialize_model_for_audit(item),
        metadata={"session_id": item.session_id, "event_staff_id": item.event_staff_id},
        request=request,
    )


@router.post("/event-sessions/{session_id}/staff", response_model=EventSessionStaffRead, status_code=201)
def assign_show_staff(session_id: UUID, payload: EventSessionStaffCreate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    item = service.create_assignment(db, session_id, payload, current_user)
    _audit(db, request, current_user, "SHOW_STAFF_ASSIGNED", item)
    return item


@router.get("/event-sessions/{session_id}/staff", response_model=EventSessionStaffListResponse)
def list_show_staff(session_id: UUID, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    items, total = service.list_assignments(db, session_id, current_user, page, limit)
    return EventSessionStaffListResponse(items=items, total=total, page=page, limit=limit)


@router.patch("/event-session-staff/{assignment_id}", response_model=EventSessionStaffRead)
def update_show_staff(assignment_id: UUID, payload: EventSessionStaffUpdate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    existing = service._assignment(db, assignment_id)
    old_data = serialize_model_for_audit(existing)
    item = service.update_assignment(db, assignment_id, payload, current_user)
    _audit(db, request, current_user, "SHOW_STAFF_UPDATED", item, old_data)
    return item


@router.delete("/event-session-staff/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_show_staff(assignment_id: UUID, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    item = service._assignment(db, assignment_id)
    old_data = serialize_model_for_audit(item)
    removed = service.delete_assignment(db, assignment_id, current_user)
    create_audit_log(db, user=current_user, action="SHOW_STAFF_REMOVED", module="event_session_staff", entity_type="EventSessionStaff", entity_id=assignment_id, event_id=removed.event_id, old_data=old_data, metadata={"session_id": removed.session_id}, request=request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/event-staff/{event_staff_id}/sessions", response_model=list[EventSessionStaffRead])
def list_person_shows(event_staff_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return service.list_person_sessions(db, event_staff_id, current_user)


@router.get("/event-sessions/{session_id}/operations/summary", response_model=ShowOperationalSummary)
def show_summary(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return service.operational_summary(db, session_id, current_user)
