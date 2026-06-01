from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.core import Client, User
from app.models.enums import UserRole
from app.schemas.user_schema import UserCreate, UserUpdate


def get_user_or_404(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def ensure_email_available(db: Session, email: str, exclude_user_id: UUID | None = None) -> None:
    statement = select(User).where(User.email == email)
    if exclude_user_id:
        statement = statement.where(User.id != exclude_user_id)
    if db.scalar(statement):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")


def validate_role_and_client(db: Session, role: UserRole, client_id: UUID | None) -> None:
    if role == UserRole.CLIENT and client_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id is required for CLIENT users",
        )
    if client_id is not None:
        client = db.get(Client, client_id)
        if not client or not client.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="client_id must reference an active client",
            )


def create_user(db: Session, payload: UserCreate, actor: User) -> User:
    if payload.role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPER_ADMIN can create SUPER_ADMIN users",
        )
    validate_role_and_client(db, payload.role, payload.client_id)
    ensure_email_available(db, payload.email)

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        client_id=payload.client_id,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc
    db.refresh(user)
    return user


def list_users(
    db: Session,
    *,
    q: str | None,
    role: UserRole | None,
    is_active: bool | None,
    client_id: UUID | None,
    page: int,
    limit: int,
) -> tuple[list[User], int]:
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
    if role:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active == is_active)
    if client_id:
        filters.append(User.client_id == client_id)

    base = select(User).where(*filters)
    total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    items = list(
        db.scalars(
            base.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
        ).all()
    )
    return items, total


def update_user(db: Session, user_id: UUID, payload: UserUpdate, actor: User) -> User:
    user = get_user_or_404(db, user_id)

    if actor.role == UserRole.ADMIN and user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ADMIN cannot modify SUPER_ADMIN users",
        )
    if payload.role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPER_ADMIN can promote users to SUPER_ADMIN",
        )

    data = payload.model_dump(exclude_unset=True)
    effective_role = data.get("role", user.role)
    effective_client_id = data.get("client_id", user.client_id)
    validate_role_and_client(db, effective_role, effective_client_id)

    for field in ("full_name", "phone", "role", "client_id", "is_active"):
        if field in data:
            setattr(user, field, data[field])
    if payload.password:
        user.password_hash = hash_password(payload.password)
    user.updated_at = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: UUID, actor: User) -> User:
    user = get_user_or_404(db, user_id)

    if actor.role == UserRole.ADMIN and user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ADMIN cannot deactivate SUPER_ADMIN users",
        )

    if user.id == actor.id and user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        remaining_admins = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.id != user.id,
                User.is_active == True,  # noqa: E712
                User.role.in_([UserRole.SUPER_ADMIN, UserRole.ADMIN]),
            )
        )
        if not remaining_admins:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active admin user",
            )

    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

