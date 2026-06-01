from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.schemas.service_schema import (
    ServiceCreate,
    ServiceListResponse,
    ServiceRead,
    ServiceUpdate,
)
from app.services import service_service

router = APIRouter(prefix="/services", tags=["services"])


@router.post(
    "",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db)):
    return service_service.create_service(db, payload)


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
def update_service(service_id: UUID, payload: ServiceUpdate, db: Session = Depends(get_db)):
    return service_service.update_service(db, service_id, payload)


@router.delete(
    "/{service_id}",
    response_model=ServiceRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def delete_service(service_id: UUID, db: Session = Depends(get_db)):
    return service_service.deactivate_service(db, service_id)
