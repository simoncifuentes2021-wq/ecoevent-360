from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.staff_schema import EventStaffCreate, EventStaffListResponse, EventStaffRead
from app.services import staff_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/events", tags=["event staff"])


@router.post(
    "/{event_id}/staff",
    response_model=EventStaffRead,
    status_code=status.HTTP_201_CREATED,
)
def assign_staff(
    event_id: UUID,
    payload: EventStaffCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    staff = staff_service.assign_staff(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="STAFF_ASSIGNED",
        module="staff",
        entity_type="EventStaff",
        entity_id=staff.id,
        event_id=staff.event_id,
        new_data=serialize_model_for_audit(staff),
        metadata={"assigned_user_id": staff.user_id, "role_in_event": staff.role_in_event},
        request=request,
    )
    return staff


@router.get("/{event_id}/staff", response_model=EventStaffListResponse)
def list_event_staff(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items = staff_service.list_event_staff(db, event_id, current_user)
    return EventStaffListResponse(items=items, total=len(items))


@router.delete("/{event_id}/staff/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_staff(
    event_id: UUID,
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    staff_service.remove_staff(db, event_id, user_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="STAFF_REMOVED",
        module="staff",
        entity_type="EventStaff",
        event_id=event_id,
        metadata={"removed_user_id": user_id},
        request=request,
    )
