from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.staff_schema import EventStaffCreate, EventStaffListResponse, EventStaffRead
from app.services import staff_service

router = APIRouter(prefix="/events", tags=["event staff"])


@router.post(
    "/{event_id}/staff",
    response_model=EventStaffRead,
    status_code=status.HTTP_201_CREATED,
)
def assign_staff(
    event_id: UUID,
    payload: EventStaffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return staff_service.assign_staff(db, event_id, payload, current_user)


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    staff_service.remove_staff(db, event_id, user_id, current_user)
