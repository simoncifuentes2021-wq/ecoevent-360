from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.service_schema import (
    ServiceCreate,
    ServiceListResponse,
    ServiceRead,
    ServiceUpdate,
)
from app.services import service_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/services", tags=["services"])


@router.post(
    "",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_service(
    payload: ServiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = service_service.create_service(db, payload)
    create_audit_log(
        db,
        user=current_user,
        action="SERVICE_CREATED",
        module="services",
        entity_type="Service",
        entity_id=service.id,
        new_data=serialize_model_for_audit(service),
        request=request,
    )
    return service


@router.get(
    "",
    response_model=ServiceListResponse,
    dependencies=[
        Depends(
            require_roles(
                UserRole.SUPER_ADMIN,
                UserRole.ADMIN,
                UserRole.SUPERVISOR,
                UserRole.CLIENT,
            )
        )
    ],
)
def list_services(
    q: str | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = service_service.list_services(
        db, q=q, is_active=is_active, page=page, limit=limit
    )
    return ServiceListResponse(items=items, total=total, page=page, limit=limit)


@router.get(
    "/{service_id}",
    response_model=ServiceRead,
    dependencies=[
        Depends(
            require_roles(
                UserRole.SUPER_ADMIN,
                UserRole.ADMIN,
                UserRole.SUPERVISOR,
                UserRole.CLIENT,
            )
        )
    ],
)
def get_service(service_id: UUID, db: Session = Depends(get_db)):
    return service_service.get_service_or_404(db, service_id)


@router.patch(
    "/{service_id}",
    response_model=ServiceRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_service(
    service_id: UUID,
    payload: ServiceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = service_service.get_service_or_404(db, service_id)
    old_data = serialize_model_for_audit(before)
    service = service_service.update_service(db, service_id, payload)
    create_audit_log(
        db,
        user=current_user,
        action="SERVICE_UPDATED",
        module="services",
        entity_type="Service",
        entity_id=service.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(service),
        request=request,
    )
    return service


@router.delete(
    "/{service_id}",
    response_model=ServiceRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def delete_service(
    service_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = service_service.get_service_or_404(db, service_id)
    old_data = serialize_model_for_audit(before)
    service = service_service.deactivate_service(db, service_id)
    create_audit_log(
        db,
        user=current_user,
        action="SERVICE_DEACTIVATED",
        module="services",
        entity_type="Service",
        entity_id=service.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(service),
        request=request,
    )
    return service
