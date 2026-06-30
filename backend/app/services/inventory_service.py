from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.core import InventoryItem, User
from app.models.enums import InventoryItemType, UserRole
from app.schemas.inventory_schema import InventoryItemCreate, InventoryItemUpdate

INVENTORY_VIEW_ROLES = {
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.SUPERVISOR,
    UserRole.LOGISTICS_OPERATOR,
}
INVENTORY_WRITE_ROLES = {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.LOGISTICS_OPERATOR}


def can_view_inventory_items(user: User) -> bool:
    return user.role in INVENTORY_VIEW_ROLES


def can_write_inventory_items(user: User) -> bool:
    return user.role in INVENTORY_WRITE_ROLES


def can_manage_inventory_item_state(user: User) -> bool:
    return user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}


def get_inventory_item_or_404(db: Session, item_id: UUID) -> InventoryItem:
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return item


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    return cleaned


def _normalize_return_required(
    item_type: InventoryItemType, return_required: bool | None = None
) -> bool:
    if item_type == InventoryItemType.RETURNABLE:
        return True
    if item_type in {InventoryItemType.CONSUMABLE, InventoryItemType.DISPOSABLE}:
        return False
    return bool(return_required) if return_required is not None else False


def _ensure_non_negative(value: Decimal | None, field: str) -> None:
    if value is not None and value < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} must be greater than or equal to 0",
        )


def _ensure_integer(value: Decimal | None, field: str) -> None:
    if value is not None and value != value.to_integral_value():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} must be an integer",
        )


def ensure_active_name_available(db: Session, name: str, exclude_item_id: UUID | None = None) -> None:
    normalized = name.strip().lower()
    statement = select(InventoryItem.id).where(
        InventoryItem.is_active == True,  # noqa: E712
        func.lower(func.trim(InventoryItem.name)) == normalized,
    )
    if exclude_item_id:
        statement = statement.where(InventoryItem.id != exclude_item_id)
    if db.scalar(statement):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active inventory item with this name already exists",
        )


def ensure_can_access_item(db: Session, user: User, item_id: UUID) -> InventoryItem:
    if not can_view_inventory_items(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    item = get_inventory_item_or_404(db, item_id)
    if user.role == UserRole.SUPERVISOR and not item.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return item


def create_inventory_item(db: Session, payload: InventoryItemCreate, user: User) -> InventoryItem:
    if not can_write_inventory_items(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    data = payload.model_dump()
    data["name"] = _clean_name(data["name"])
    data["return_required"] = _normalize_return_required(
        data["item_type"], data.get("return_required")
    )
    _ensure_non_negative(data.get("replacement_cost"), "replacement_cost")
    _ensure_non_negative(data.get("min_stock"), "min_stock")
    _ensure_integer(data.get("min_stock"), "min_stock")
    _ensure_non_negative(data.get("unit_price"), "unit_price")
    ensure_active_name_available(db, data["name"])
    item = InventoryItem(**data, is_active=True, created_by=user.id)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active inventory item with this name already exists",
        ) from exc
    db.refresh(item)
    return item


def list_inventory_items(
    db: Session,
    *,
    user: User,
    q: str | None,
    item_type: InventoryItemType | None,
    is_active: bool | None,
    page: int,
    limit: int,
) -> tuple[list[InventoryItem], int]:
    if not can_view_inventory_items(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                InventoryItem.name.ilike(pattern),
                InventoryItem.sku.ilike(pattern),
                InventoryItem.description.ilike(pattern),
            )
        )
    if item_type:
        filters.append(InventoryItem.item_type == item_type)
    if user.role == UserRole.SUPERVISOR:
        filters.append(InventoryItem.is_active == True)  # noqa: E712
    elif is_active is not None:
        filters.append(InventoryItem.is_active == is_active)

    total = db.scalar(select(func.count()).select_from(InventoryItem).where(*filters)) or 0
    items = list(
        db.scalars(
            select(InventoryItem)
            .where(*filters)
            .order_by(InventoryItem.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def update_inventory_item(
    db: Session, item_id: UUID, payload: InventoryItemUpdate, user: User
) -> InventoryItem:
    if not can_write_inventory_items(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    item = get_inventory_item_or_404(db, item_id)
    data = payload.model_dump(exclude_unset=True)
    if "is_active" in data and not can_manage_inventory_item_state(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN or SUPER_ADMIN can change item state",
        )
    if "name" in data and data["name"] is not None:
        data["name"] = _clean_name(data["name"])
    if "replacement_cost" in data:
        _ensure_non_negative(data["replacement_cost"], "replacement_cost")
    if "min_stock" in data:
        _ensure_non_negative(data["min_stock"], "min_stock")
        _ensure_integer(data["min_stock"], "min_stock")
    if "unit_price" in data:
        _ensure_non_negative(data["unit_price"], "unit_price")

    effective_name = data.get("name", item.name)
    effective_is_active = data.get("is_active", item.is_active)
    if effective_is_active:
        ensure_active_name_available(db, effective_name, exclude_item_id=item_id)

    effective_type = data.get("item_type", item.item_type)
    if "item_type" in data or "return_required" in data:
        data["return_required"] = _normalize_return_required(
            effective_type, data.get("return_required", item.return_required)
        )

    for field, value in data.items():
        setattr(item, field, value)
    item.updated_at = datetime.utcnow()
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active inventory item with this name already exists",
        ) from exc
    db.refresh(item)
    return item


def deactivate_inventory_item(db: Session, item_id: UUID) -> InventoryItem:
    item = get_inventory_item_or_404(db, item_id)
    item.is_active = False
    item.updated_at = datetime.utcnow()
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
