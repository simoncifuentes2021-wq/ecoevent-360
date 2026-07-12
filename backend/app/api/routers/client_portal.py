from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.client_portal_schema import ClientPortalResponse
from app.services import client_portal_service

router = APIRouter(prefix="/client/events", tags=["client portal"])


@router.get(
    "/{event_id}/portal",
    response_model=ClientPortalResponse,
    dependencies=[Depends(require_roles(UserRole.CLIENT))],
)
def get_client_event_portal(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return client_portal_service.client_portal(db, event_id, current_user)
