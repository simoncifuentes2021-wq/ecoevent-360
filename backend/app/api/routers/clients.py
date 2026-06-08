from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.core.permissions import can_access_client
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.client_schema import (
    ClientCreate,
    ClientEventListResponse,
    ClientListResponse,
    ClientRead,
    ClientUpdate,
)
from app.services import client_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post(
    "",
    response_model=ClientRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_client(
    payload: ClientCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    client = client_service.create_client(db, payload)
    create_audit_log(
        db,
        user=current_user,
        action="CLIENT_CREATED",
        module="clients",
        entity_type="Client",
        entity_id=client.id,
        client_id=client.id,
        new_data=serialize_model_for_audit(client),
        request=request,
    )
    return client


@router.get(
    "",
    response_model=ClientListResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def list_clients(
    q: str | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = client_service.list_clients(
        db, q=q, is_active=is_active, page=page, limit=limit
    )
    return ClientListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    client = client_service.get_client_or_404(db, client_id)
    if not can_access_client(current_user, client_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return client


@router.patch(
    "/{client_id}",
    response_model=ClientRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = client_service.get_client_or_404(db, client_id)
    old_data = serialize_model_for_audit(before)
    client = client_service.update_client(db, client_id, payload)
    create_audit_log(
        db,
        user=current_user,
        action="CLIENT_UPDATED",
        module="clients",
        entity_type="Client",
        entity_id=client.id,
        client_id=client.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(client),
        request=request,
    )
    return client


@router.delete(
    "/{client_id}",
    response_model=ClientRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
def delete_client(
    client_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = client_service.get_client_or_404(db, client_id)
    old_data = serialize_model_for_audit(before)
    client = client_service.deactivate_client(db, client_id)
    create_audit_log(
        db,
        user=current_user,
        action="CLIENT_DEACTIVATED",
        module="clients",
        entity_type="Client",
        entity_id=client.id,
        client_id=client.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(client),
        request=request,
    )
    return client


@router.get("/{client_id}/events", response_model=ClientEventListResponse)
def list_client_events(
    client_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    client_service.get_client_or_404(db, client_id)
    if not can_access_client(current_user, client_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    items, total = client_service.list_client_events(
        db, client_id=client_id, page=page, limit=limit
    )
    return ClientEventListResponse(items=items, total=total, page=page, limit=limit)
