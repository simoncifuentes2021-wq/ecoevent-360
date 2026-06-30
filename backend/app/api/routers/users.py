from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.user_schema import UserCreate, UserListResponse, UserRead, UserUpdate
from app.services import user_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    user = user_service.create_user(db, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="USER_CREATED",
        module="users",
        entity_type="User",
        entity_id=user.id,
        client_id=user.client_id,
        new_data=serialize_model_for_audit(user),
        request=request,
    )
    return user


@router.get(
    "",
    response_model=UserListResponse,
)
def list_users(
    q: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    client_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        supervisor_operational_lookup = (
            current_user.role == UserRole.SUPERVISOR
            and role in {UserRole.SUPERVISOR, UserRole.WORKER, UserRole.LOGISTICS_OPERATOR}
            and is_active is True
            and client_id is None
        )
        supervisor_operator_lookup = (
            current_user.role == UserRole.SUPERVISOR
            and role == UserRole.LOGISTICS_OPERATOR
            and is_active is True
            and client_id is None
        )
        if not supervisor_operational_lookup and not supervisor_operator_lookup:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    items, total = user_service.list_users(
        db,
        q=q,
        role=role,
        is_active=is_active,
        client_id=client_id,
        page=page,
        limit=limit,
    )
    return UserListResponse(items=items, total=total, page=page, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    return user_service.get_user_or_404(db, user_id)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = user_service.get_user_or_404(db, user_id)
    old_data = serialize_model_for_audit(before)
    old_role = before.role
    user = user_service.update_user(db, user_id, payload, current_user)
    if payload.password is not None:
        create_audit_log(
            db,
            user=current_user,
            action="USER_PASSWORD_CHANGED",
            module="users",
            entity_type="User",
            entity_id=user.id,
            client_id=user.client_id,
            old_data={"password": "[REDACTED]"},
            new_data={"password": "[REDACTED]"},
            request=request,
        )
    action = "USER_ROLE_CHANGED" if old_role != user.role else "USER_UPDATED"
    create_audit_log(
        db,
        user=current_user,
        action=action,
        module="users",
        entity_type="User",
        entity_id=user.id,
        client_id=user.client_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(user),
        request=request,
    )
    return user


@router.delete(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def delete_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = user_service.get_user_or_404(db, user_id)
    old_data = serialize_model_for_audit(before)
    user = user_service.deactivate_user(db, user_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="USER_DEACTIVATED",
        module="users",
        entity_type="User",
        entity_id=user.id,
        client_id=user.client_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(user),
        request=request,
    )
    return user
