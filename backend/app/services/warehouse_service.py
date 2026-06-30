from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.core import User, Warehouse, WarehouseUser
from app.models.enums import UserRole
from app.schemas.warehouse_schema import WarehouseCreate, WarehouseUpdate, WarehouseUserCreate, WarehouseUserUpdate

WAREHOUSE_VIEW_ROLES = {
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.SUPERVISOR,
    UserRole.LOGISTICS_OPERATOR,
}
WAREHOUSE_ASSIGNABLE_ROLES = {
    UserRole.LOGISTICS_OPERATOR,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
}


def can_view_warehouses(user: User) -> bool:
    return user.role in WAREHOUSE_VIEW_ROLES


def can_manage_warehouses(user: User) -> bool:
    return user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}


def get_warehouse_or_404(db: Session, warehouse_id: UUID) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return warehouse


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required",
        )
    return cleaned


def ensure_can_access_warehouse(db: Session, user: User, warehouse_id: UUID) -> Warehouse:
    warehouse = get_warehouse_or_404(db, warehouse_id)
    if not can_view_warehouses(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if user.role == UserRole.LOGISTICS_OPERATOR:
        assigned = db.scalar(
            select(WarehouseUser.id).where(
                WarehouseUser.warehouse_id == warehouse_id,
                WarehouseUser.user_id == user.id,
            )
        )
        if assigned is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if user.role in {UserRole.SUPERVISOR, UserRole.LOGISTICS_OPERATOR} and not warehouse.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return warehouse


def ensure_active_name_available(
    db: Session, name: str, exclude_warehouse_id: UUID | None = None
) -> None:
    normalized = name.strip().lower()
    statement = select(Warehouse.id).where(
        Warehouse.is_active == True,  # noqa: E712
        func.lower(func.trim(Warehouse.name)) == normalized,
    )
    if exclude_warehouse_id:
        statement = statement.where(Warehouse.id != exclude_warehouse_id)
    if db.scalar(statement):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active warehouse with this name already exists",
        )


def create_warehouse(db: Session, payload: WarehouseCreate) -> Warehouse:
    data = payload.model_dump()
    data["name"] = _clean_name(data["name"])
    ensure_active_name_available(db, data["name"])
    warehouse = Warehouse(**data, is_active=True)
    db.add(warehouse)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active warehouse with this name already exists",
        ) from exc
    db.refresh(warehouse)
    return warehouse


def list_warehouses(
    db: Session,
    *,
    user: User,
    q: str | None,
    is_active: bool | None,
    page: int,
    limit: int,
) -> tuple[list[Warehouse], int]:
    if not can_view_warehouses(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                Warehouse.name.ilike(pattern),
                Warehouse.city.ilike(pattern),
                Warehouse.address.ilike(pattern),
                Warehouse.notes.ilike(pattern),
            )
        )
    if user.role in {UserRole.SUPERVISOR, UserRole.LOGISTICS_OPERATOR}:
        filters.append(Warehouse.is_active == True)  # noqa: E712
    elif is_active is not None:
        filters.append(Warehouse.is_active == is_active)

    statement = select(Warehouse).where(*filters)
    count_statement = select(func.count()).select_from(Warehouse).where(*filters)

    if user.role == UserRole.LOGISTICS_OPERATOR:
        statement = statement.join(WarehouseUser).where(WarehouseUser.user_id == user.id)
        count_statement = (
            select(func.count())
            .select_from(Warehouse)
            .join(WarehouseUser)
            .where(*filters, WarehouseUser.user_id == user.id)
        )

    total = db.scalar(count_statement) or 0
    items = list(
        db.scalars(
            statement.order_by(Warehouse.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def update_warehouse(db: Session, warehouse_id: UUID, payload: WarehouseUpdate) -> Warehouse:
    warehouse = get_warehouse_or_404(db, warehouse_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        data["name"] = _clean_name(data["name"])
    effective_name = data.get("name", warehouse.name)
    effective_is_active = data.get("is_active", warehouse.is_active)
    if effective_is_active:
        ensure_active_name_available(db, effective_name, exclude_warehouse_id=warehouse_id)
    for field, value in data.items():
        setattr(warehouse, field, value)
    warehouse.updated_at = datetime.utcnow()
    db.add(warehouse)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active warehouse with this name already exists",
        ) from exc
    db.refresh(warehouse)
    return warehouse


def deactivate_warehouse(db: Session, warehouse_id: UUID) -> Warehouse:
    warehouse = get_warehouse_or_404(db, warehouse_id)
    warehouse.is_active = False
    warehouse.updated_at = datetime.utcnow()
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


def assign_warehouse_user(
    db: Session, warehouse_id: UUID, payload: WarehouseUserCreate
) -> WarehouseUser:
    get_warehouse_or_404(db, warehouse_id)
    user = db.get(User, payload.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role not in WAREHOUSE_ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be LOGISTICS_OPERATOR, ADMIN or SUPER_ADMIN",
        )
    assignment = WarehouseUser(warehouse_id=warehouse_id, **payload.model_dump())
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already assigned to this warehouse",
        ) from exc
    db.refresh(assignment)
    return assignment


def list_warehouse_users(db: Session, warehouse_id: UUID) -> list[WarehouseUser]:
    get_warehouse_or_404(db, warehouse_id)
    return list(
        db.scalars(
            select(WarehouseUser)
            .options(selectinload(WarehouseUser.user))
            .where(WarehouseUser.warehouse_id == warehouse_id)
            .order_by(WarehouseUser.created_at.desc())
        ).all()
    )


def update_warehouse_user(
    db: Session, warehouse_id: UUID, user_id: UUID, payload: WarehouseUserUpdate
) -> WarehouseUser:
    assignment = db.scalar(
        select(WarehouseUser)
        .options(selectinload(WarehouseUser.user))
        .where(
            WarehouseUser.warehouse_id == warehouse_id,
            WarehouseUser.user_id == user_id,
        )
    )
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("can_manage_stock") and data.get("can_view_stock") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="can_view_stock is required to manage stock",
        )
    for field, value in data.items():
        setattr(assignment, field, value)
    if assignment.can_manage_stock and not assignment.can_view_stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="can_view_stock is required to manage stock",
        )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def list_my_warehouse_assignments(db: Session, user: User) -> list[WarehouseUser]:
    if user.role != UserRole.LOGISTICS_OPERATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return list(
        db.scalars(
            select(WarehouseUser)
            .options(selectinload(WarehouseUser.warehouse))
            .join(WarehouseUser.warehouse)
            .where(
                WarehouseUser.user_id == user.id,
                Warehouse.is_active == True,  # noqa: E712
            )
            .order_by(Warehouse.name.asc())
        ).all()
    )


def remove_warehouse_user(db: Session, warehouse_id: UUID, user_id: UUID) -> None:
    assignment = db.scalar(
        select(WarehouseUser).where(
            WarehouseUser.warehouse_id == warehouse_id,
            WarehouseUser.user_id == user_id,
        )
    )
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
