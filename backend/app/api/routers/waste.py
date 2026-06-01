from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.waste_schema import (
    WasteRecordCreate,
    WasteRecordListResponse,
    WasteRecordRead,
    WasteRecordUpdate,
    WasteSummaryRead,
    WasteTypeCreate,
    WasteTypeListResponse,
    WasteTypeRead,
    WasteTypeUpdate,
)
from app.services import waste_service

router = APIRouter(tags=["waste"])


@router.get("/waste-types", response_model=WasteTypeListResponse)
def list_waste_types(
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = waste_service.list_waste_types(db, q=q, page=page, limit=limit)
    return WasteTypeListResponse(items=items, total=total, page=page, limit=limit)


@router.post(
    "/waste-types",
    response_model=WasteTypeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_waste_type(payload: WasteTypeCreate, db: Session = Depends(get_db)):
    return waste_service.create_waste_type(db, payload)


@router.patch(
    "/waste-types/{waste_type_id}",
    response_model=WasteTypeRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_waste_type(
    waste_type_id: UUID,
    payload: WasteTypeUpdate,
    db: Session = Depends(get_db),
):
    return waste_service.update_waste_type(db, waste_type_id, payload)


@router.delete(
    "/waste-types/{waste_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def delete_waste_type(waste_type_id: UUID, db: Session = Depends(get_db)):
    waste_service.delete_waste_type(db, waste_type_id)


@router.post(
    "/events/{event_id}/waste-records",
    response_model=WasteRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_waste_record(
    event_id: UUID,
    payload: WasteRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return waste_service.create_waste_record(db, event_id, payload, current_user)


@router.get("/events/{event_id}/waste-records", response_model=WasteRecordListResponse)
def list_event_waste_records(
    event_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = waste_service.list_event_waste_records(
        db, event_id=event_id, current_user=current_user, page=page, limit=limit
    )
    return WasteRecordListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/waste-records/{record_id}", response_model=WasteRecordRead)
def get_waste_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return waste_service.get_waste_record(db, record_id, current_user)


@router.patch("/waste-records/{record_id}", response_model=WasteRecordRead)
def update_waste_record(
    record_id: UUID,
    payload: WasteRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return waste_service.update_waste_record(db, record_id, payload, current_user)


@router.delete("/waste-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_waste_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    waste_service.delete_waste_record(db, record_id, current_user)


@router.get("/events/{event_id}/waste-summary", response_model=WasteSummaryRead)
def get_waste_summary(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return waste_service.get_waste_summary(db, event_id, current_user)
