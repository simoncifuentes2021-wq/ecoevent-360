from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.dashboard_schema import (
    AdminDashboardResponse,
    ClientDashboardResponse,
    EventDashboardResponse,
    WorkerDashboardResponse,
)
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/admin",
    response_model=AdminDashboardResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def get_admin_dashboard(db: Session = Depends(get_db)):
    return dashboard_service.get_admin_dashboard(db)


@router.get(
    "/client",
    response_model=ClientDashboardResponse,
    dependencies=[Depends(require_roles(UserRole.CLIENT))],
)
def get_client_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return dashboard_service.get_client_dashboard(db, current_user)


@router.get(
    "/worker",
    response_model=WorkerDashboardResponse,
    dependencies=[Depends(require_roles(UserRole.WORKER, UserRole.SUPERVISOR))],
)
def get_worker_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return dashboard_service.get_worker_dashboard(db, current_user)


@router.get("/events/{event_id}", response_model=EventDashboardResponse)
def get_event_dashboard_alias(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Deprecated compatibility alias. Prefer GET /events/{event_id}/dashboard.
    return dashboard_service.get_event_dashboard(db, event_id, current_user)
