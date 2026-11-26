from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.field_checklist_schema import (
    ChecklistHistoryRead, ChecklistItemCreate, ChecklistItemRead, ChecklistItemUpdate,
    ChecklistPersonRead,
)
from app.services import field_checklist_service as service

router = APIRouter(tags=["field checklists"])
allowed_roles = (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR)


@router.get("/events/{event_id}/field-checklists/people", response_model=list[ChecklistPersonRead])
def list_people(event_id: UUID, db: Session = Depends(get_db), actor: User = Depends(require_roles(*allowed_roles))):
    return service.list_people(db, event_id, actor)


@router.get("/field-checklists/email-status")
def email_status(actor: User = Depends(require_roles(*allowed_roles))):
    return service.email_status()


@router.get("/events/{event_id}/field-checklists", response_model=list[ChecklistItemRead])
def list_items(event_id: UUID, owner_id: UUID | None = None, db: Session = Depends(get_db), actor: User = Depends(require_roles(*allowed_roles))):
    return service.list_items(db, event_id, actor, owner_id)


@router.post("/events/{event_id}/field-checklists", response_model=ChecklistItemRead, status_code=status.HTTP_201_CREATED)
def create_item(event_id: UUID, payload: ChecklistItemCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(*allowed_roles))):
    return service.create_item(db, event_id, payload, actor)


@router.patch("/field-checklists/{item_id}", response_model=ChecklistItemRead)
def update_item(item_id: UUID, payload: ChecklistItemUpdate, db: Session = Depends(get_db), actor: User = Depends(require_roles(*allowed_roles))):
    return service.update_item(db, item_id, payload, actor)


@router.get("/field-checklists/{item_id}/history", response_model=list[ChecklistHistoryRead])
def list_history(item_id: UUID, db: Session = Depends(get_db), actor: User = Depends(require_roles(*allowed_roles))):
    return service.list_history(db, item_id, actor)
