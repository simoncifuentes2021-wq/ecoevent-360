from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.user_schema import UserCreate, UserListResponse, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return user_service.create_user(db, payload, current_user)


@router.get(
    "",
    response_model=UserListResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def list_users(
    q: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    client_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return user_service.update_user(db, user_id, payload, current_user)


@router.delete(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return user_service.deactivate_user(db, user_id, current_user)

