from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import can_access_event, can_create_logistics_order, can_manage_event
from app.models.core import (
    Event,
    InventoryItem,
    LogisticsOrder,
    LogisticsOrderItem,
    StockBalance,
    StockMovement,
    User,
    Warehouse,
    WarehouseUser,
)
from app.models.enums import LogisticsOrderStatus, StockMovementType, UserRole
from app.schemas.logistics_order_schema import (
    LogisticsOrderAssign,
    LogisticsOrderClose,
    LogisticsOrderCreate,
    LogisticsOrderDeliveryConfirm,
    LogisticsOrderDispatch,
    LogisticsOrderItemCreate,
    LogisticsOrderItemDeliver,
    LogisticsOrderItemLoad,
    LogisticsOrderItemOutcome,
    LogisticsOrderItemUpdate,
    LogisticsOrderOutcomeConfirm,
    LogisticsOrderStockCheckItem,
    LogisticsOrderStockCheckResponse,
    LogisticsOrderUpdate,
)

MANAGE_STATUSES = {
    LogisticsOrderStatus.REQUESTED,
    LogisticsOrderStatus.ASSIGNED,
    LogisticsOrderStatus.STOCK_REVIEW,
    LogisticsOrderStatus.INSUFFICIENT_STOCK,
    LogisticsOrderStatus.OBSERVED,
}


def _load_order_query():
    return select(LogisticsOrder).options(
        selectinload(LogisticsOrder.items),
        selectinload(LogisticsOrder.event),
        selectinload(LogisticsOrder.warehouse),
        selectinload(LogisticsOrder.requester),
        selectinload(LogisticsOrder.assigned_operator),
    )


def get_logistics_order_or_404(db: Session, order_id: UUID) -> LogisticsOrder:
    order = db.scalar(_load_order_query().where(LogisticsOrder.id == order_id))
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logistics order not found")
    return order


def get_logistics_order_item_or_404(db: Session, item_id: UUID) -> LogisticsOrderItem:
    item = db.get(LogisticsOrderItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logistics order item not found")
    return item


def _ensure_active_warehouse(db: Session, warehouse_id: UUID) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return warehouse


def _ensure_active_inventory_item(db: Session, item_id: UUID) -> InventoryItem:
    item = db.get(InventoryItem, item_id)
    if not item or not item.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return item


def _ensure_operator(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned operator not found")
    if user.role != UserRole.LOGISTICS_OPERATOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="assigned_operator_id must belong to a LOGISTICS_OPERATOR",
        )
    return user


def _ensure_can_view_order(user: User, order: LogisticsOrder, db: Session) -> None:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return
    if user.role == UserRole.SUPERVISOR and can_access_event(user, order.event_id, db):
        return
    if user.role == UserRole.LOGISTICS_OPERATOR and order.assigned_operator_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_manage_order(user: User, order: LogisticsOrder, db: Session) -> None:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return
    if user.role == UserRole.SUPERVISOR and can_manage_event(user, order.event_id, db):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_review_stock(user: User, order: LogisticsOrder, db: Session) -> None:
    _ensure_can_view_order(user, order, db)
    if user.role in {UserRole.WORKER, UserRole.CLIENT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_reserve_stock(user: User, order: LogisticsOrder) -> None:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return
    if user.role == UserRole.LOGISTICS_OPERATOR and order.assigned_operator_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_operate_order_warehouse(db: Session, user: User, order: LogisticsOrder) -> None:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return
    if user.role != UserRole.LOGISTICS_OPERATOR or order.assigned_operator_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    assignment = db.scalar(
        select(WarehouseUser).where(
            WarehouseUser.user_id == user.id,
            WarehouseUser.warehouse_id == order.warehouse_id,
        )
    )
    if not assignment or not assignment.can_view_stock or not assignment.can_dispatch_orders:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para operar pedidos en la bodega del pedido",
        )


def _ensure_mutable(order: LogisticsOrder) -> None:
    if order.status == LogisticsOrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify cancelled logistics orders",
        )
    if order.status == LogisticsOrderStatus.RESERVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify reserved logistics orders. Release the reservation first.",
        )


def _calculate_total(quantity: Decimal, unit_price: Decimal) -> Decimal:
    return quantity * unit_price


def _available_quantity(stock: StockBalance | None) -> Decimal:
    if not stock:
        return Decimal("0")
    return stock.quantity_on_hand - stock.quantity_reserved - stock.quantity_damaged


def _get_stock_balance(
    db: Session,
    *,
    warehouse_id: UUID,
    item_id: UUID,
    lock: bool = False,
) -> StockBalance | None:
    statement = select(StockBalance).where(
        StockBalance.warehouse_id == warehouse_id,
        StockBalance.item_id == item_id,
    )
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def _record_reservation_movement(
    db: Session,
    *,
    order: LogisticsOrder,
    stock: StockBalance,
    movement_type: StockMovementType,
    quantity: Decimal,
    previous_reserved: Decimal,
    new_reserved: Decimal,
    user: User,
    previous_on_hand: Decimal | None = None,
    new_on_hand: Decimal | None = None,
    previous_damaged: Decimal | None = None,
    new_damaged: Decimal | None = None,
) -> None:
    reason = (
        f"Reserva pedido logistico {order.title}"
        if movement_type == StockMovementType.RESERVE
        else f"Liberacion reserva pedido logistico {order.title}"
        if movement_type == StockMovementType.UNRESERVE
        else f"Salida de bodega por pedido logistico {order.title}"
    )
    notes = f"Pedido logistico {order.id} - Evento {order.event_id}"
    db.add(
        StockMovement(
            warehouse_id=stock.warehouse_id,
            item_id=stock.item_id,
            stock_balance_id=stock.id,
            movement_type=movement_type,
            quantity=quantity,
            previous_quantity_on_hand=previous_on_hand if previous_on_hand is not None else stock.quantity_on_hand,
            new_quantity_on_hand=new_on_hand if new_on_hand is not None else stock.quantity_on_hand,
            previous_quantity_reserved=previous_reserved,
            new_quantity_reserved=new_reserved,
            previous_quantity_damaged=previous_damaged if previous_damaged is not None else stock.quantity_damaged,
            new_quantity_damaged=new_damaged if new_damaged is not None else stock.quantity_damaged,
            reference_type="LOGISTICS_ORDER",
            reference_id=order.id,
            reason=reason,
            notes=notes,
            created_by=user.id,
        )
    )


def _record_outcome_movement(
    db: Session,
    *,
    order: LogisticsOrder,
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
    notes: str | None,
) -> None:
    movement_label = (
        "Retorno desde evento"
        if movement_type == StockMovementType.RETURN_FROM_EVENT
        else "Producto devuelto danado"
    )
    db.add(
        StockMovement(
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
            reference_type="LOGISTICS_ORDER",
            reference_id=order.id,
            reason=f"{movement_label} por resultado pedido logistico {order.title}",
            notes=notes or f"Pedido logistico {order.id} - Evento {order.event_id}",
            created_by=user.id,
        )
    )


def _outcome_total(item: LogisticsOrderItem) -> Decimal:
    return (
        item.quantity_consumed
        + item.quantity_returned
        + item.quantity_returned_damaged
        + item.quantity_lost
        + item.quantity_discarded
    )


def _outcome_status(total: Decimal, delivered: Decimal) -> str:
    if total == 0:
        return "PENDING"
    if total == delivered:
        return "RECORDED"
    return "PARTIAL"


def _ensure_outcome_order_state(order: LogisticsOrder) -> None:
    if order.status not in {
        LogisticsOrderStatus.DELIVERED,
        LogisticsOrderStatus.PARTIALLY_DELIVERED,
        LogisticsOrderStatus.OUTCOME_PENDING,
        LogisticsOrderStatus.WITH_DIFFERENCES,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only delivered logistics orders can register outcomes",
        )


def _get_or_create_stock_balance_for_return(
    db: Session,
    *,
    warehouse_id: UUID,
    item_id: UUID,
) -> StockBalance:
    stock = _get_stock_balance(db, warehouse_id=warehouse_id, item_id=item_id, lock=True)
    if stock:
        return stock
    stock = StockBalance(
        warehouse_id=warehouse_id,
        item_id=item_id,
        quantity_on_hand=Decimal("0"),
        quantity_reserved=Decimal("0"),
        quantity_damaged=Decimal("0"),
    )
    db.add(stock)
    db.flush()
    return stock


def _recalculate_order_total(db: Session, order: LogisticsOrder) -> None:
    total = db.scalar(
        select(func.coalesce(func.sum(LogisticsOrderItem.total_price), 0)).where(
            LogisticsOrderItem.order_id == order.id
        )
    )
    order.total_estimated_amount = Decimal(total or 0)
    order.updated_at = datetime.utcnow()
    db.add(order)


def _build_order_item(order_id: UUID, payload: LogisticsOrderItemCreate, item: InventoryItem) -> LogisticsOrderItem:
    unit_price = item.unit_price or Decimal("0")
    return LogisticsOrderItem(
        order_id=order_id,
        item_id=item.id,
        item_name_snapshot=item.name,
        item_type_snapshot=item.item_type.value,
        unit_snapshot=item.unit,
        quantity_requested=payload.quantity_requested,
        unit_price_snapshot=unit_price,
        total_price=_calculate_total(payload.quantity_requested, unit_price),
        notes=payload.notes,
    )


def create_logistics_order(
    db: Session, event_id: UUID, payload: LogisticsOrderCreate, user: User
) -> LogisticsOrder:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if not can_create_logistics_order(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    _ensure_active_warehouse(db, payload.warehouse_id)
    _ensure_operator(db, payload.assigned_operator_id)
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order requires items")

    order = LogisticsOrder(
        event_id=event_id,
        warehouse_id=payload.warehouse_id,
        requested_by=user.id,
        assigned_operator_id=payload.assigned_operator_id,
        status=LogisticsOrderStatus.ASSIGNED,
        title=payload.title,
        description=payload.description,
        delivery_zone=payload.delivery_zone,
        delivery_notes=payload.delivery_notes,
    )
    db.add(order)
    db.flush()
    for item_payload in payload.items:
        inventory_item = _ensure_active_inventory_item(db, item_payload.item_id)
        db.add(_build_order_item(order.id, item_payload, inventory_item))
    db.flush()
    _recalculate_order_total(db, order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def list_logistics_orders(
    db: Session,
    *,
    user: User,
    event_id: UUID | None,
    status_filter: LogisticsOrderStatus | None,
    assigned_operator_id: UUID | None,
    q: str | None,
    page: int,
    limit: int,
) -> tuple[list[LogisticsOrder], int]:
    filters = []
    if event_id:
        event = db.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        if user.role == UserRole.WORKER:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        if user.role != UserRole.LOGISTICS_OPERATOR and not can_access_event(user, event_id, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        filters.append(LogisticsOrder.event_id == event_id)

    if user.role in {UserRole.WORKER, UserRole.CLIENT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if user.role == UserRole.LOGISTICS_OPERATOR:
        filters.append(LogisticsOrder.assigned_operator_id == user.id)
    elif user.role == UserRole.SUPERVISOR:
        filters.append(
            LogisticsOrder.event_id.in_(
                select(Event.id).where(Event.id == LogisticsOrder.event_id)
            )
        )

    if status_filter:
        filters.append(LogisticsOrder.status == status_filter)
    if assigned_operator_id:
        filters.append(LogisticsOrder.assigned_operator_id == assigned_operator_id)
    if q:
        pattern = f"%{q}%"
        filters.append(or_(LogisticsOrder.title.ilike(pattern), LogisticsOrder.description.ilike(pattern)))

    statement = _load_order_query().where(*filters)
    count_statement = select(func.count()).select_from(LogisticsOrder).where(*filters)

    if user.role == UserRole.SUPERVISOR and event_id is None:
        # Keep supervisor visibility aligned with event access by filtering in memory for this stage.
        all_orders = list(
            db.scalars(statement.order_by(LogisticsOrder.created_at.desc())).all()
        )
        visible = [order for order in all_orders if can_access_event(user, order.event_id, db)]
        total = len(visible)
        return visible[(page - 1) * limit : (page - 1) * limit + limit], total

    total = db.scalar(count_statement) or 0
    items = list(
        db.scalars(
            statement.order_by(LogisticsOrder.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def get_logistics_order_detail(db: Session, order_id: UUID, user: User) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_view_order(user, order, db)
    return order


def update_logistics_order(
    db: Session, order_id: UUID, payload: LogisticsOrderUpdate, user: User
) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_manage_order(user, order, db)
    _ensure_mutable(order)
    data = payload.model_dump(exclude_unset=True)
    if "warehouse_id" in data:
        _ensure_active_warehouse(db, data["warehouse_id"])
    for field, value in data.items():
        setattr(order, field, value)
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def assign_logistics_order(
    db: Session, order_id: UUID, payload: LogisticsOrderAssign, user: User
) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_manage_order(user, order, db)
    _ensure_mutable(order)
    _ensure_operator(db, payload.assigned_operator_id)
    order.assigned_operator_id = payload.assigned_operator_id
    order.status = LogisticsOrderStatus.ASSIGNED
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def cancel_logistics_order(db: Session, order_id: UUID, user: User) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_manage_order(user, order, db)
    order.status = LogisticsOrderStatus.CANCELLED
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def check_logistics_order_stock(
    db: Session, order_id: UUID, user: User
) -> LogisticsOrderStockCheckResponse:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_review_stock(user, order, db)
    if order.status == LogisticsOrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot review stock for cancelled logistics orders",
        )

    warehouse = db.get(Warehouse, order.warehouse_id)
    if not warehouse or not warehouse.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    checks: list[LogisticsOrderStockCheckItem] = []
    for order_item in order.items:
        inventory_item = db.get(InventoryItem, order_item.item_id)
        stock = _get_stock_balance(
            db,
            warehouse_id=order.warehouse_id,
            item_id=order_item.item_id,
        )
        available = _available_quantity(stock) if inventory_item and inventory_item.is_active else Decimal("0")
        missing = max(order_item.quantity_requested - available, Decimal("0"))
        checks.append(
            LogisticsOrderStockCheckItem(
                item_id=order_item.item_id,
                item_name_snapshot=order_item.item_name_snapshot,
                quantity_requested=order_item.quantity_requested,
                quantity_reserved=order_item.quantity_reserved,
                warehouse_id=order.warehouse_id,
                warehouse_name=warehouse.name,
                quantity_on_hand=stock.quantity_on_hand if stock else Decimal("0"),
                quantity_reserved_in_stock=stock.quantity_reserved if stock else Decimal("0"),
                quantity_damaged=stock.quantity_damaged if stock else Decimal("0"),
                available_quantity=available,
                missing_quantity=missing,
                can_reserve=missing == 0 and bool(inventory_item and inventory_item.is_active),
            )
        )

    return LogisticsOrderStockCheckResponse(
        order_id=order.id,
        status=order.status,
        warehouse_id=order.warehouse_id,
        warehouse_name=warehouse.name,
        can_reserve_all=all(item.can_reserve for item in checks) and bool(checks),
        items=checks,
    )


def reserve_logistics_order_stock(db: Session, order_id: UUID, user: User) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    if order.status == LogisticsOrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reserve stock for cancelled logistics orders",
        )
    if order.status == LogisticsOrderStatus.RESERVED or any(
        item.quantity_reserved > 0 for item in order.items
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logistics order is already reserved")

    warehouse = db.get(Warehouse, order.warehouse_id)
    if not warehouse or not warehouse.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    stocks_by_item: dict[UUID, StockBalance] = {}
    missing_items: list[LogisticsOrderItem] = []
    for order_item in order.items:
        inventory_item = db.get(InventoryItem, order_item.item_id)
        stock = _get_stock_balance(
            db,
            warehouse_id=order.warehouse_id,
            item_id=order_item.item_id,
            lock=True,
        )
        available = _available_quantity(stock) if inventory_item and inventory_item.is_active else Decimal("0")
        missing = max(order_item.quantity_requested - available, Decimal("0"))
        order_item.quantity_missing = missing
        order_item.reservation_status = "INSUFFICIENT_STOCK" if missing > 0 else "PENDING"
        db.add(order_item)
        if missing > 0 or not stock or not inventory_item or not inventory_item.is_active:
            missing_items.append(order_item)
        else:
            stocks_by_item[order_item.item_id] = stock

    if missing_items:
        order.status = LogisticsOrderStatus.INSUFFICIENT_STOCK
        order.reserved_at = None
        order.reserved_by = None
        order.updated_at = datetime.utcnow()
        db.add(order)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "No hay stock suficiente para reservar este pedido",
                "missing_items": [
                    {
                        "item_id": str(item.id),
                        "item_name_snapshot": item.item_name_snapshot,
                        "quantity_requested": str(item.quantity_requested),
                        "quantity_missing": str(item.quantity_missing),
                    }
                    for item in missing_items
                ],
            },
        )

    for order_item in order.items:
        stock = stocks_by_item[order_item.item_id]
        previous_reserved = stock.quantity_reserved
        new_reserved = previous_reserved + order_item.quantity_requested
        if stock.quantity_on_hand - new_reserved - stock.quantity_damaged < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stock availability changed while reserving the order",
            )
        stock.quantity_reserved = new_reserved
        stock.updated_at = datetime.utcnow()
        order_item.quantity_reserved = order_item.quantity_requested
        order_item.quantity_missing = Decimal("0")
        order_item.reservation_status = "RESERVED"
        order_item.updated_at = datetime.utcnow()
        db.add(stock)
        db.add(order_item)
        _record_reservation_movement(
            db,
            order=order,
            stock=stock,
            movement_type=StockMovementType.RESERVE,
            quantity=order_item.quantity_requested,
            previous_reserved=previous_reserved,
            new_reserved=new_reserved,
            user=user,
        )

    order.status = LogisticsOrderStatus.RESERVED
    order.reserved_at = datetime.utcnow()
    order.reserved_by = user.id
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def unreserve_logistics_order_stock(db: Session, order_id: UUID, user: User) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    if order.status == LogisticsOrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unreserve stock for cancelled logistics orders",
        )

    reserved_items = [item for item in order.items if item.quantity_reserved > 0]
    if not reserved_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logistics order has no reserved stock")

    for order_item in reserved_items:
        stock = _get_stock_balance(
            db,
            warehouse_id=order.warehouse_id,
            item_id=order_item.item_id,
            lock=True,
        )
        if not stock:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock balance not found")
        previous_reserved = stock.quantity_reserved
        new_reserved = previous_reserved - order_item.quantity_reserved
        if new_reserved < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reserved stock cannot become negative",
            )
        stock.quantity_reserved = new_reserved
        stock.updated_at = datetime.utcnow()
        _record_reservation_movement(
            db,
            order=order,
            stock=stock,
            movement_type=StockMovementType.UNRESERVE,
            quantity=order_item.quantity_reserved,
            previous_reserved=previous_reserved,
            new_reserved=new_reserved,
            user=user,
        )
        order_item.quantity_reserved = Decimal("0")
        order_item.quantity_missing = Decimal("0")
        order_item.reservation_status = "PENDING"
        order_item.updated_at = datetime.utcnow()
        db.add(stock)
        db.add(order_item)

    for order_item in order.items:
        if order_item not in reserved_items:
            order_item.quantity_missing = Decimal("0")
            order_item.reservation_status = "PENDING"
            order_item.updated_at = datetime.utcnow()
            db.add(order_item)

    order.status = LogisticsOrderStatus.ASSIGNED
    order.reserved_at = None
    order.reserved_by = None
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def start_logistics_order_preparation(db: Session, order_id: UUID, user: User) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    if order.status == LogisticsOrderStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot prepare cancelled logistics orders")
    if order.status != LogisticsOrderStatus.RESERVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only reserved logistics orders can enter preparation")
    order.status = LogisticsOrderStatus.IN_PREPARATION
    order.prepared_at = datetime.utcnow()
    order.prepared_by = user.id
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def load_logistics_order_item(
    db: Session, item_id: UUID, payload: LogisticsOrderItemLoad, user: User
) -> LogisticsOrderItem:
    order_item = get_logistics_order_item_or_404(db, item_id)
    order = get_logistics_order_or_404(db, order_item.order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    if order.status == LogisticsOrderStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot load cancelled logistics orders")
    if order.status not in {LogisticsOrderStatus.RESERVED, LogisticsOrderStatus.IN_PREPARATION, LogisticsOrderStatus.LOADED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only reserved orders can be loaded")
    if order_item.quantity_reserved <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order item has no reserved quantity")
    if payload.quantity_loaded > order_item.quantity_reserved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity_loaded cannot exceed quantity_reserved")

    order_item.quantity_loaded = payload.quantity_loaded
    order_item.preparation_status = (
        "LOADED" if payload.quantity_loaded == order_item.quantity_reserved else "PARTIALLY_LOADED"
    )
    if payload.notes is not None:
        order_item.notes = payload.notes
    order_item.updated_at = datetime.utcnow()
    db.add(order_item)

    db.flush()
    items = list(
        db.scalars(select(LogisticsOrderItem).where(LogisticsOrderItem.order_id == order.id)).all()
    )
    if items and all(item.quantity_loaded == item.quantity_reserved and item.quantity_reserved > 0 for item in items):
        order.status = LogisticsOrderStatus.LOADED
    else:
        order.status = LogisticsOrderStatus.IN_PREPARATION
    if not order.prepared_at:
        order.prepared_at = datetime.utcnow()
        order.prepared_by = user.id
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    db.refresh(order_item)
    return order_item


def dispatch_logistics_order(
    db: Session, order_id: UUID, payload: LogisticsOrderDispatch, user: User
) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    if order.status == LogisticsOrderStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot dispatch cancelled logistics orders")
    if order.status == LogisticsOrderStatus.OUT_OF_WAREHOUSE or order.dispatched_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logistics order already left warehouse")
    if order.status not in {LogisticsOrderStatus.IN_PREPARATION, LogisticsOrderStatus.LOADED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only loaded orders can leave warehouse")
    if not order.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logistics order has no items")
    if any(item.quantity_loaded <= 0 for item in order.items):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All items require loaded quantity before dispatch")
    if any(item.quantity_loaded != item.quantity_reserved for item in order.items):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complete loading is required before dispatch")

    for order_item in order.items:
        stock = _get_stock_balance(
            db,
            warehouse_id=order.warehouse_id,
            item_id=order_item.item_id,
            lock=True,
        )
        if not stock:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock balance not found")
        if stock.quantity_reserved < order_item.quantity_loaded:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reserved stock is lower than loaded quantity")
        previous_on_hand = stock.quantity_on_hand
        previous_reserved = stock.quantity_reserved
        previous_damaged = stock.quantity_damaged
        new_on_hand = previous_on_hand - order_item.quantity_loaded
        new_reserved = previous_reserved - order_item.quantity_loaded
        if new_on_hand < 0 or new_reserved < 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stock cannot become negative")
        stock.quantity_on_hand = new_on_hand
        stock.quantity_reserved = new_reserved
        stock.updated_at = datetime.utcnow()
        order_item.quantity_dispatched = order_item.quantity_loaded
        order_item.updated_at = datetime.utcnow()
        db.add(stock)
        db.add(order_item)
        _record_reservation_movement(
            db,
            order=order,
            stock=stock,
            movement_type=StockMovementType.OUT_TO_EVENT,
            quantity=order_item.quantity_loaded,
            previous_reserved=previous_reserved,
            new_reserved=new_reserved,
            user=user,
            previous_on_hand=previous_on_hand,
            new_on_hand=new_on_hand,
            previous_damaged=previous_damaged,
            new_damaged=stock.quantity_damaged,
        )

    order.status = LogisticsOrderStatus.OUT_OF_WAREHOUSE
    order.dispatched_at = datetime.utcnow()
    order.dispatched_by = user.id
    order.dispatch_notes = payload.dispatch_notes
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def deliver_logistics_order_item(
    db: Session, item_id: UUID, payload: LogisticsOrderItemDeliver, user: User
) -> LogisticsOrderItem:
    order_item = get_logistics_order_item_or_404(db, item_id)
    order = get_logistics_order_or_404(db, order_item.order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    if order.status == LogisticsOrderStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deliver cancelled logistics orders")
    if order.status not in {LogisticsOrderStatus.OUT_OF_WAREHOUSE, LogisticsOrderStatus.PARTIALLY_DELIVERED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only orders out of warehouse can register field delivery",
        )
    if order_item.quantity_dispatched <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order item has no dispatched quantity")
    if payload.quantity_delivered > order_item.quantity_dispatched:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quantity_delivered cannot exceed quantity_dispatched",
        )

    order_item.quantity_delivered = payload.quantity_delivered
    order_item.delivery_status = (
        "DELIVERED" if payload.quantity_delivered == order_item.quantity_dispatched else "PARTIALLY_DELIVERED"
    )
    if payload.notes is not None:
        order_item.notes = payload.notes
    order_item.updated_at = datetime.utcnow()
    db.add(order_item)
    db.commit()
    db.refresh(order_item)
    return order_item


def confirm_logistics_order_delivery(
    db: Session, order_id: UUID, payload: LogisticsOrderDeliveryConfirm, user: User
) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    if order.status == LogisticsOrderStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deliver cancelled logistics orders")
    if order.status != LogisticsOrderStatus.OUT_OF_WAREHOUSE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only orders out of warehouse can confirm field delivery",
        )
    if not order.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logistics order has no items")
    if any(item.quantity_dispatched <= 0 for item in order.items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All items require dispatched quantity before delivery",
        )
    if any(item.quantity_delivered > item.quantity_dispatched for item in order.items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivered quantity cannot exceed dispatched quantity",
        )
    if not any(item.quantity_delivered > 0 for item in order.items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one delivered quantity is required before confirming delivery",
        )

    all_delivered = all(item.quantity_delivered == item.quantity_dispatched for item in order.items)
    for order_item in order.items:
        order_item.delivery_status = "DELIVERED" if order_item.quantity_delivered == order_item.quantity_dispatched else "PARTIALLY_DELIVERED"
        order_item.updated_at = datetime.utcnow()
        db.add(order_item)

    order.status = LogisticsOrderStatus.DELIVERED if all_delivered else LogisticsOrderStatus.PARTIALLY_DELIVERED
    order.delivered_at = datetime.utcnow()
    order.delivered_by = user.id
    if payload.delivery_notes is not None:
        order.delivery_notes = payload.delivery_notes
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def register_logistics_order_item_outcome(
    db: Session, item_id: UUID, payload: LogisticsOrderItemOutcome, user: User
) -> LogisticsOrderItem:
    order_item = get_logistics_order_item_or_404(db, item_id)
    order = get_logistics_order_or_404(db, order_item.order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    _ensure_outcome_order_state(order)
    if order_item.quantity_delivered <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order item has no delivered quantity")

    total = (
        payload.quantity_consumed
        + payload.quantity_returned
        + payload.quantity_returned_damaged
        + payload.quantity_lost
        + payload.quantity_discarded
    )
    if total > order_item.quantity_delivered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outcome quantities cannot exceed quantity_delivered",
        )
    if payload.quantity_returned < order_item.quantity_returned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quantity_returned cannot be lower than the previously recorded returned quantity",
        )
    if payload.quantity_returned_damaged < order_item.quantity_returned_damaged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quantity_returned_damaged cannot be lower than the previously recorded damaged returned quantity",
        )
    if order_item.item_type_snapshot == "RETURNABLE" and payload.quantity_consumed > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RETURNABLE items cannot be marked as consumed",
        )

    delta_returned = payload.quantity_returned - order_item.quantity_returned
    delta_returned_damaged = payload.quantity_returned_damaged - order_item.quantity_returned_damaged
    if delta_returned > 0 or delta_returned_damaged > 0:
        stock = _get_or_create_stock_balance_for_return(
            db,
            warehouse_id=order.warehouse_id,
            item_id=order_item.item_id,
        )
        if delta_returned > 0:
            previous_on_hand = stock.quantity_on_hand
            previous_reserved = stock.quantity_reserved
            previous_damaged = stock.quantity_damaged
            stock.quantity_on_hand = previous_on_hand + delta_returned
            stock.updated_at = datetime.utcnow()
            db.add(stock)
            _record_outcome_movement(
                db,
                order=order,
                stock=stock,
                movement_type=StockMovementType.RETURN_FROM_EVENT,
                quantity=delta_returned,
                previous_on_hand=previous_on_hand,
                new_on_hand=stock.quantity_on_hand,
                previous_reserved=previous_reserved,
                new_reserved=stock.quantity_reserved,
                previous_damaged=previous_damaged,
                new_damaged=stock.quantity_damaged,
                user=user,
                notes=payload.notes,
            )
        if delta_returned_damaged > 0:
            previous_on_hand = stock.quantity_on_hand
            previous_reserved = stock.quantity_reserved
            previous_damaged = stock.quantity_damaged
            stock.quantity_on_hand = previous_on_hand + delta_returned_damaged
            stock.updated_at = datetime.utcnow()
            db.add(stock)
            _record_outcome_movement(
                db,
                order=order,
                stock=stock,
                movement_type=StockMovementType.RETURN_FROM_EVENT,
                quantity=delta_returned_damaged,
                previous_on_hand=previous_on_hand,
                new_on_hand=stock.quantity_on_hand,
                previous_reserved=previous_reserved,
                new_reserved=stock.quantity_reserved,
                previous_damaged=previous_damaged,
                new_damaged=stock.quantity_damaged,
                user=user,
                notes=payload.notes,
            )

            previous_on_hand = stock.quantity_on_hand
            previous_reserved = stock.quantity_reserved
            previous_damaged = stock.quantity_damaged
            stock.quantity_damaged = previous_damaged + delta_returned_damaged
            stock.updated_at = datetime.utcnow()
            db.add(stock)
            _record_outcome_movement(
                db,
                order=order,
                stock=stock,
                movement_type=StockMovementType.DAMAGE,
                quantity=delta_returned_damaged,
                previous_on_hand=previous_on_hand,
                new_on_hand=stock.quantity_on_hand,
                previous_reserved=previous_reserved,
                new_reserved=stock.quantity_reserved,
                previous_damaged=previous_damaged,
                new_damaged=stock.quantity_damaged,
                user=user,
                notes=payload.notes,
            )

    order_item.quantity_consumed = payload.quantity_consumed
    order_item.quantity_returned = payload.quantity_returned
    order_item.quantity_returned_damaged = payload.quantity_returned_damaged
    order_item.quantity_lost = payload.quantity_lost
    order_item.quantity_discarded = payload.quantity_discarded
    order_item.outcome_status = _outcome_status(total, order_item.quantity_delivered)
    order_item.outcome_notes = payload.notes
    order_item.updated_at = datetime.utcnow()
    db.add(order_item)

    if order.status in {LogisticsOrderStatus.DELIVERED, LogisticsOrderStatus.PARTIALLY_DELIVERED}:
        order.status = LogisticsOrderStatus.OUTCOME_PENDING
        order.updated_at = datetime.utcnow()
        db.add(order)

    db.commit()
    db.refresh(order_item)
    return order_item


def confirm_logistics_order_outcome(
    db: Session, order_id: UUID, payload: LogisticsOrderOutcomeConfirm, user: User
) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    _ensure_outcome_order_state(order)
    if not order.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logistics order has no items")
    if any(item.quantity_delivered <= 0 for item in order.items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All items require delivered quantity before confirming outcomes",
        )

    all_explained = True
    for order_item in order.items:
        total = _outcome_total(order_item)
        if total > order_item.quantity_delivered:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Outcome quantities cannot exceed quantity_delivered",
            )
        if total < order_item.quantity_delivered:
            all_explained = False
            order_item.outcome_status = "PARTIAL" if total > 0 else "PENDING"
        else:
            order_item.outcome_status = "RECORDED"
        order_item.updated_at = datetime.utcnow()
        db.add(order_item)

    order.status = LogisticsOrderStatus.OUTCOME_RECORDED if all_explained else LogisticsOrderStatus.WITH_DIFFERENCES
    order.outcome_recorded_at = datetime.utcnow()
    order.outcome_recorded_by = user.id
    order.outcome_notes = payload.outcome_notes
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def close_logistics_order(db: Session, order_id: UUID, payload: LogisticsOrderClose, user: User) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    if order.status == LogisticsOrderStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot close cancelled logistics orders")
    if order.status == LogisticsOrderStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logistics order is already closed")
    if order.status == LogisticsOrderStatus.WITH_DIFFERENCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot close logistics order with unexplained differences",
        )
    if order.status != LogisticsOrderStatus.OUTCOME_RECORDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only orders with recorded outcomes can be closed",
        )
    if not order.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logistics order has no items")

    for order_item in order.items:
        explained = _outcome_total(order_item)
        if explained != order_item.quantity_delivered:
            pending = order_item.quantity_delivered - explained
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No se puede cerrar el pedido. "
                    f"El producto {order_item.item_name_snapshot} tiene "
                    f"{order_item.quantity_delivered} entregadas, {explained} explicadas y {pending} pendientes."
                ),
            )

    order.status = LogisticsOrderStatus.CLOSED
    order.closed_at = datetime.utcnow()
    order.closed_by = user.id
    order.closure_notes = payload.closure_notes
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def add_logistics_order_item(
    db: Session, order_id: UUID, payload: LogisticsOrderItemCreate, user: User
) -> LogisticsOrderItem:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_manage_order(user, order, db)
    _ensure_mutable(order)
    item = _ensure_active_inventory_item(db, payload.item_id)
    order_item = _build_order_item(order.id, payload, item)
    db.add(order_item)
    db.flush()
    _recalculate_order_total(db, order)
    db.commit()
    db.refresh(order_item)
    return order_item


def update_logistics_order_item(
    db: Session, item_id: UUID, payload: LogisticsOrderItemUpdate, user: User
) -> LogisticsOrderItem:
    order_item = get_logistics_order_item_or_404(db, item_id)
    order = get_logistics_order_or_404(db, order_item.order_id)
    _ensure_can_manage_order(user, order, db)
    _ensure_mutable(order)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(order_item, field, value)
    order_item.total_price = _calculate_total(
        order_item.quantity_requested, order_item.unit_price_snapshot
    )
    order_item.updated_at = datetime.utcnow()
    db.add(order_item)
    _recalculate_order_total(db, order)
    db.commit()
    db.refresh(order_item)
    return order_item


def delete_logistics_order_item(db: Session, item_id: UUID, user: User) -> None:
    order_item = get_logistics_order_item_or_404(db, item_id)
    order = get_logistics_order_or_404(db, order_item.order_id)
    _ensure_can_manage_order(user, order, db)
    _ensure_mutable(order)
    count = db.scalar(
        select(func.count()).select_from(LogisticsOrderItem).where(LogisticsOrderItem.order_id == order.id)
    )
    if count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last item from a logistics order",
        )
    db.delete(order_item)
    db.flush()
    _recalculate_order_total(db, order)
    db.commit()
