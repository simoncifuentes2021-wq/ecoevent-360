from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.core import InventoryItem, StockBalance, StockMovement, User, Warehouse, WarehouseUser
from app.models.enums import StockMovementType, UserRole
from app.schemas.stock_schema import (
    StockBalanceCreate,
    StockBalanceRead,
    StockBalanceUpdate,
    StockMovementCreate,
    StockMovementRead,
)

STOCK_VIEW_ROLES = {
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.SUPERVISOR,
    UserRole.LOGISTICS_OPERATOR,
}
STOCK_MANAGE_ROLES = {UserRole.SUPER_ADMIN, UserRole.ADMIN}


def can_view_stock(user: User) -> bool:
    return user.role in STOCK_VIEW_ROLES


def can_manage_stock(user: User) -> bool:
    return user.role in STOCK_MANAGE_ROLES


def _operator_stock_assignment(db: Session, user: User, warehouse_id: UUID) -> WarehouseUser | None:
    if user.role != UserRole.LOGISTICS_OPERATOR:
        return None
    return db.scalar(
        select(WarehouseUser).where(
            WarehouseUser.user_id == user.id,
            WarehouseUser.warehouse_id == warehouse_id,
        )
    )


def _ensure_can_view_warehouse_stock(db: Session, user: User, warehouse_id: UUID) -> None:
    if not can_view_stock(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if user.role == UserRole.LOGISTICS_OPERATOR:
        assignment = _operator_stock_assignment(db, user, warehouse_id)
        if not assignment or not assignment.can_view_stock:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_manage_warehouse_stock(db: Session, user: User, warehouse_id: UUID) -> None:
    if can_manage_stock(user):
        return
    if user.role == UserRole.LOGISTICS_OPERATOR:
        assignment = _operator_stock_assignment(db, user, warehouse_id)
        if assignment and assignment.can_manage_stock:
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_active_warehouse(db: Session, warehouse_id: UUID) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return warehouse


def _ensure_active_item(db: Session, item_id: UUID) -> InventoryItem:
    item = db.get(InventoryItem, item_id)
    if not item or not item.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return item


def get_stock_balance_or_404(db: Session, stock_id: UUID) -> StockBalance:
    stock = db.scalar(
        select(StockBalance)
        .options(joinedload(StockBalance.warehouse), joinedload(StockBalance.item))
        .where(StockBalance.id == stock_id)
    )
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock balance not found")
    return stock


def _validate_quantities(
    quantity_on_hand: Decimal,
    quantity_reserved: Decimal,
    quantity_damaged: Decimal,
) -> None:
    values = {
        "quantity_on_hand": quantity_on_hand,
        "quantity_reserved": quantity_reserved,
        "quantity_damaged": quantity_damaged,
    }
    for field, value in values.items():
        if value < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} must be greater than or equal to 0",
            )
    if quantity_reserved > quantity_on_hand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quantity_reserved cannot be greater than quantity_on_hand",
        )
    if quantity_damaged > quantity_on_hand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quantity_damaged cannot be greater than quantity_on_hand",
        )
    if quantity_on_hand - quantity_reserved - quantity_damaged < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="available_quantity cannot be negative",
        )


def _stock_query():
    return select(StockBalance).options(
        joinedload(StockBalance.warehouse),
        joinedload(StockBalance.item),
    )


def _stock_filters(
    *,
    warehouse_id: UUID | None,
    item_id: UUID | None,
    q: str | None,
    low_stock: bool | None,
) -> list:
    filters = [
        Warehouse.is_active == True,  # noqa: E712
        InventoryItem.is_active == True,  # noqa: E712
    ]
    if warehouse_id:
        filters.append(StockBalance.warehouse_id == warehouse_id)
    if item_id:
        filters.append(StockBalance.item_id == item_id)
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                InventoryItem.name.ilike(pattern),
                InventoryItem.sku.ilike(pattern),
                Warehouse.name.ilike(pattern),
            )
        )
    if low_stock is not None:
        available = (
            StockBalance.quantity_on_hand
            - StockBalance.quantity_reserved
            - StockBalance.quantity_damaged
        )
        condition = available <= InventoryItem.min_stock
        filters.append(condition if low_stock else ~condition)
    return filters


def list_stock_balances(
    db: Session,
    *,
    user: User,
    warehouse_id: UUID | None,
    item_id: UUID | None,
    q: str | None,
    low_stock: bool | None,
    page: int,
    limit: int,
) -> tuple[list[StockBalance], int]:
    if not can_view_stock(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    filters = _stock_filters(warehouse_id=warehouse_id, item_id=item_id, q=q, low_stock=low_stock)
    statement = _stock_query().join(StockBalance.warehouse).join(StockBalance.item).where(*filters)
    count_statement = (
        select(func.count())
        .select_from(StockBalance)
        .join(StockBalance.warehouse)
        .join(StockBalance.item)
        .where(*filters)
    )

    if user.role == UserRole.LOGISTICS_OPERATOR:
        statement = statement.join(
            WarehouseUser,
            WarehouseUser.warehouse_id == StockBalance.warehouse_id,
        ).where(WarehouseUser.user_id == user.id, WarehouseUser.can_view_stock == True)  # noqa: E712
        count_statement = count_statement.join(
            WarehouseUser,
            WarehouseUser.warehouse_id == StockBalance.warehouse_id,
        ).where(WarehouseUser.user_id == user.id, WarehouseUser.can_view_stock == True)  # noqa: E712

    total = db.scalar(count_statement) or 0
    items = list(
        db.scalars(
            statement.order_by(Warehouse.name.asc(), InventoryItem.name.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def ensure_can_access_stock_balance(db: Session, user: User, stock_id: UUID) -> StockBalance:
    stock = get_stock_balance_or_404(db, stock_id)
    _ensure_can_view_warehouse_stock(db, user, stock.warehouse_id)
    if not stock.warehouse.is_active or not stock.item.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock balance not found")
    return stock


def _get_stock_balance_by_pair(
    db: Session, warehouse_id: UUID, item_id: UUID, *, lock: bool = False
) -> StockBalance | None:
    statement = select(StockBalance).where(
        StockBalance.warehouse_id == warehouse_id,
        StockBalance.item_id == item_id,
    )
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def _record_stock_movement(
    db: Session,
    *,
    stock: StockBalance,
    movement_type: StockMovementType,
    quantity: Decimal,
    previous_on_hand: Decimal,
    new_on_hand: Decimal,
    previous_reserved: Decimal,
    new_reserved: Decimal,
    previous_damaged: Decimal,
    new_damaged: Decimal,
    user: User,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    reason: str | None = None,
    notes: str | None = None,
) -> StockMovement:
    movement = StockMovement(
        warehouse_id=stock.warehouse_id,
        item_id=stock.item_id,
        stock_balance_id=stock.id,
        movement_type=movement_type,
        quantity=quantity,
        previous_quantity_on_hand=previous_on_hand,
        new_quantity_on_hand=new_on_hand,
        previous_quantity_reserved=previous_reserved,
        new_quantity_reserved=new_reserved,
        previous_quantity_damaged=previous_damaged,
        new_quantity_damaged=new_damaged,
        reference_type=reference_type,
        reference_id=reference_id,
        reason=reason,
        notes=notes,
        created_by=user.id,
    )
    db.add(movement)
    return movement


def _load_stock_movement_or_404(db: Session, movement_id: UUID) -> StockMovement:
    movement = db.scalar(
        select(StockMovement)
        .options(
            joinedload(StockMovement.warehouse),
            joinedload(StockMovement.item),
            joinedload(StockMovement.creator),
        )
        .where(StockMovement.id == movement_id)
    )
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock movement not found")
    return movement


def create_stock_balance(db: Session, payload: StockBalanceCreate, user: User) -> StockBalance:
    _ensure_can_manage_warehouse_stock(db, user, payload.warehouse_id)
    _ensure_active_warehouse(db, payload.warehouse_id)
    _ensure_active_item(db, payload.item_id)
    data = payload.model_dump()
    _validate_quantities(
        data["quantity_on_hand"],
        data["quantity_reserved"],
        data["quantity_damaged"],
    )
    existing = _get_stock_balance_by_pair(db, payload.warehouse_id, payload.item_id, lock=True)
    if existing:
        previous_on_hand = existing.quantity_on_hand
        previous_reserved = existing.quantity_reserved
        previous_damaged = existing.quantity_damaged
        existing.quantity_on_hand = data["quantity_on_hand"]
        existing.quantity_reserved = data["quantity_reserved"]
        existing.quantity_damaged = data["quantity_damaged"]
        existing.updated_at = datetime.utcnow()
        correction_quantity = max(
            abs(existing.quantity_on_hand - previous_on_hand),
            abs(existing.quantity_reserved - previous_reserved),
            abs(existing.quantity_damaged - previous_damaged),
            Decimal("1"),
        )
        _record_stock_movement(
            db,
            stock=existing,
            movement_type=StockMovementType.CORRECTION,
            quantity=correction_quantity,
            previous_on_hand=previous_on_hand,
            new_on_hand=existing.quantity_on_hand,
            previous_reserved=previous_reserved,
            new_reserved=existing.quantity_reserved,
            previous_damaged=previous_damaged,
            new_damaged=existing.quantity_damaged,
            user=user,
            reason="Ajuste directo desde balance de stock",
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return get_stock_balance_or_404(db, existing.id)

    stock = StockBalance(**data)
    db.add(stock)
    db.flush()
    _record_stock_movement(
        db,
        stock=stock,
        movement_type=StockMovementType.INITIAL_STOCK,
        quantity=data["quantity_on_hand"] if data["quantity_on_hand"] > 0 else Decimal("1"),
        previous_on_hand=Decimal("0"),
        new_on_hand=data["quantity_on_hand"],
        previous_reserved=Decimal("0"),
        new_reserved=data["quantity_reserved"],
        previous_damaged=Decimal("0"),
        new_damaged=data["quantity_damaged"],
        user=user,
        reason="Carga inicial de stock",
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock balance already exists for this warehouse and item",
        ) from exc
    db.refresh(stock)
    return get_stock_balance_or_404(db, stock.id)


def update_stock_balance(
    db: Session, stock_id: UUID, payload: StockBalanceUpdate, user: User
) -> StockBalance:
    stock = get_stock_balance_or_404(db, stock_id)
    _ensure_can_manage_warehouse_stock(db, user, stock.warehouse_id)
    data = payload.model_dump(exclude_unset=True)
    quantity_on_hand = data.get("quantity_on_hand", stock.quantity_on_hand)
    quantity_reserved = data.get("quantity_reserved", stock.quantity_reserved)
    quantity_damaged = data.get("quantity_damaged", stock.quantity_damaged)
    _validate_quantities(quantity_on_hand, quantity_reserved, quantity_damaged)

    previous_on_hand = stock.quantity_on_hand
    previous_reserved = stock.quantity_reserved
    previous_damaged = stock.quantity_damaged
    for field, value in data.items():
        setattr(stock, field, value)
    stock.updated_at = datetime.utcnow()
    correction_quantity = max(
        abs(stock.quantity_on_hand - previous_on_hand),
        abs(stock.quantity_reserved - previous_reserved),
        abs(stock.quantity_damaged - previous_damaged),
        Decimal("1"),
    )
    _record_stock_movement(
        db,
        stock=stock,
        movement_type=StockMovementType.CORRECTION,
        quantity=correction_quantity,
        previous_on_hand=previous_on_hand,
        new_on_hand=stock.quantity_on_hand,
        previous_reserved=previous_reserved,
        new_reserved=stock.quantity_reserved,
        previous_damaged=previous_damaged,
        new_damaged=stock.quantity_damaged,
        user=user,
        reason="Correccion directa desde balance de stock",
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return get_stock_balance_or_404(db, stock.id)


def create_stock_movement(db: Session, payload: StockMovementCreate, user: User) -> StockMovement:
    _ensure_can_manage_warehouse_stock(db, user, payload.warehouse_id)
    _ensure_active_warehouse(db, payload.warehouse_id)
    _ensure_active_item(db, payload.item_id)

    if payload.movement_type in {
        StockMovementType.PURCHASE_IN,
        StockMovementType.RESERVE,
        StockMovementType.UNRESERVE,
        StockMovementType.OUT_TO_EVENT,
        StockMovementType.RETURN_FROM_EVENT,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movement type is reserved for a future stage",
        )
    if payload.movement_type in {
        StockMovementType.CORRECTION,
        StockMovementType.LOSS,
        StockMovementType.DAMAGE,
    } and not ((payload.reason or "").strip() or (payload.notes or "").strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason or notes is required for this movement type",
        )

    stock = _get_stock_balance_by_pair(db, payload.warehouse_id, payload.item_id, lock=True)
    if not stock:
        if payload.movement_type not in {
            StockMovementType.INITIAL_STOCK,
            StockMovementType.ADJUSTMENT_IN,
        }:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock balance not found",
            )
        stock = StockBalance(
            warehouse_id=payload.warehouse_id,
            item_id=payload.item_id,
            quantity_on_hand=Decimal("0"),
            quantity_reserved=Decimal("0"),
            quantity_damaged=Decimal("0"),
        )
        db.add(stock)
        db.flush()
    elif user.role == UserRole.LOGISTICS_OPERATOR and payload.movement_type == StockMovementType.INITIAL_STOCK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INITIAL_STOCK is only allowed when the stock balance does not exist",
        )

    previous_on_hand = stock.quantity_on_hand
    previous_reserved = stock.quantity_reserved
    previous_damaged = stock.quantity_damaged
    new_on_hand = previous_on_hand
    new_reserved = previous_reserved
    new_damaged = previous_damaged

    if payload.movement_type == StockMovementType.INITIAL_STOCK:
        new_on_hand = previous_on_hand + payload.quantity
        new_reserved = (
            payload.quantity_reserved if payload.quantity_reserved is not None else previous_reserved
        )
        new_damaged = (
            payload.quantity_damaged if payload.quantity_damaged is not None else previous_damaged
        )
    elif payload.movement_type == StockMovementType.ADJUSTMENT_IN:
        new_on_hand = previous_on_hand + payload.quantity
    elif payload.movement_type == StockMovementType.ADJUSTMENT_OUT:
        new_on_hand = previous_on_hand - payload.quantity
    elif payload.movement_type == StockMovementType.DAMAGE:
        new_damaged = previous_damaged + payload.quantity
    elif payload.movement_type == StockMovementType.LOSS:
        new_on_hand = previous_on_hand - payload.quantity
    elif payload.movement_type == StockMovementType.RECOVER_DAMAGED:
        new_damaged = previous_damaged - payload.quantity
    elif payload.movement_type == StockMovementType.CORRECTION:
        new_on_hand = payload.quantity_on_hand if payload.quantity_on_hand is not None else previous_on_hand
        new_reserved = (
            payload.quantity_reserved if payload.quantity_reserved is not None else previous_reserved
        )
        new_damaged = (
            payload.quantity_damaged if payload.quantity_damaged is not None else previous_damaged
        )

    _validate_quantities(new_on_hand, new_reserved, new_damaged)

    stock.quantity_on_hand = new_on_hand
    stock.quantity_reserved = new_reserved
    stock.quantity_damaged = new_damaged
    stock.updated_at = datetime.utcnow()
    db.add(stock)
    movement = _record_stock_movement(
        db,
        stock=stock,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        previous_on_hand=previous_on_hand,
        new_on_hand=new_on_hand,
        previous_reserved=previous_reserved,
        new_reserved=new_reserved,
        previous_damaged=previous_damaged,
        new_damaged=new_damaged,
        user=user,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        reason=payload.reason,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(movement)
    return _load_stock_movement_or_404(db, movement.id)


def get_stock_movement_or_404(db: Session, movement_id: UUID) -> StockMovement:
    return _load_stock_movement_or_404(db, movement_id)


def ensure_can_access_stock_movement(db: Session, user: User, movement_id: UUID) -> StockMovement:
    movement = get_stock_movement_or_404(db, movement_id)
    _ensure_can_view_warehouse_stock(db, user, movement.warehouse_id)
    if not movement.warehouse.is_active or not movement.item.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock movement not found")
    return movement


def list_stock_movements(
    db: Session,
    *,
    user: User,
    warehouse_id: UUID | None,
    item_id: UUID | None,
    stock_balance_id: UUID | None,
    movement_type: StockMovementType | None,
    date_from: datetime | None,
    date_to: datetime | None,
    q: str | None,
    page: int,
    limit: int,
) -> tuple[list[StockMovement], int]:
    if not can_view_stock(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    filters = [
        Warehouse.is_active == True,  # noqa: E712
        InventoryItem.is_active == True,  # noqa: E712
    ]
    if warehouse_id:
        filters.append(StockMovement.warehouse_id == warehouse_id)
    if item_id:
        filters.append(StockMovement.item_id == item_id)
    if stock_balance_id:
        filters.append(StockMovement.stock_balance_id == stock_balance_id)
    if movement_type:
        filters.append(StockMovement.movement_type == movement_type)
    if date_from:
        filters.append(StockMovement.created_at >= date_from)
    if date_to:
        filters.append(StockMovement.created_at <= date_to)
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                InventoryItem.name.ilike(pattern),
                InventoryItem.sku.ilike(pattern),
                Warehouse.name.ilike(pattern),
                StockMovement.reason.ilike(pattern),
                StockMovement.notes.ilike(pattern),
            )
        )

    statement = (
        select(StockMovement)
        .options(
            joinedload(StockMovement.warehouse),
            joinedload(StockMovement.item),
            joinedload(StockMovement.creator),
        )
        .join(StockMovement.warehouse)
        .join(StockMovement.item)
        .where(*filters)
    )
    count_statement = (
        select(func.count())
        .select_from(StockMovement)
        .join(StockMovement.warehouse)
        .join(StockMovement.item)
        .where(*filters)
    )

    if user.role == UserRole.LOGISTICS_OPERATOR:
        statement = statement.join(
            WarehouseUser,
            WarehouseUser.warehouse_id == StockMovement.warehouse_id,
        ).where(WarehouseUser.user_id == user.id, WarehouseUser.can_view_stock == True)  # noqa: E712
        count_statement = count_statement.join(
            WarehouseUser,
            WarehouseUser.warehouse_id == StockMovement.warehouse_id,
        ).where(WarehouseUser.user_id == user.id, WarehouseUser.can_view_stock == True)  # noqa: E712

    total = db.scalar(count_statement) or 0
    items = list(
        db.scalars(
            statement.order_by(StockMovement.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def stock_balance_to_read(stock: StockBalance) -> StockBalanceRead:
    available = stock.quantity_on_hand - stock.quantity_reserved - stock.quantity_damaged
    unit_price = stock.item.unit_price or Decimal("0")
    return StockBalanceRead(
        id=stock.id,
        warehouse_id=stock.warehouse_id,
        warehouse_name=stock.warehouse.name,
        item_id=stock.item_id,
        item_name=stock.item.name,
        item_type=stock.item.item_type,
        unit=stock.item.unit,
        quantity_on_hand=stock.quantity_on_hand,
        quantity_reserved=stock.quantity_reserved,
        quantity_damaged=stock.quantity_damaged,
        available_quantity=available,
        min_stock=stock.item.min_stock,
        is_low_stock=available <= stock.item.min_stock,
        unit_price=unit_price,
        estimated_stock_value=stock.quantity_on_hand * unit_price,
        created_at=stock.created_at,
        updated_at=stock.updated_at,
    )


def stock_movement_to_read(movement: StockMovement) -> StockMovementRead:
    return StockMovementRead(
        id=movement.id,
        warehouse_id=movement.warehouse_id,
        warehouse_name=movement.warehouse.name,
        item_id=movement.item_id,
        item_name=movement.item.name,
        item_type=movement.item.item_type,
        stock_balance_id=movement.stock_balance_id,
        movement_type=movement.movement_type,
        quantity=movement.quantity,
        previous_quantity_on_hand=movement.previous_quantity_on_hand,
        new_quantity_on_hand=movement.new_quantity_on_hand,
        previous_quantity_reserved=movement.previous_quantity_reserved,
        new_quantity_reserved=movement.new_quantity_reserved,
        previous_quantity_damaged=movement.previous_quantity_damaged,
        new_quantity_damaged=movement.new_quantity_damaged,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        reason=movement.reason,
        notes=movement.notes,
        created_by=movement.created_by,
        created_by_name=movement.creator.full_name if movement.creator else None,
        created_at=movement.created_at,
    )
