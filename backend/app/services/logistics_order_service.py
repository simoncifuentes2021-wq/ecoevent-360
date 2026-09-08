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
    LogisticsEvidence,
    LogisticsOrder,
    LogisticsOrderItem,
    LogisticsPartialDispatchRequest,
    PurchaseRequest,
    StockBalance,
    StockMovement,
    User,
    Warehouse,
    WarehouseUser,
)
from app.models.enums import (
    LogisticsEvidenceStage,
    LogisticsOrderStatus,
    PurchaseRequestStatus,
    StockMovementType,
    UserRole,
)
from app.schemas.logistics_order_schema import (
    LogisticsOrderAssign,
    LogisticsOrderAvailabilityResponse,
    LogisticsOrderClose,
    LogisticsOrderCreate,
    LogisticsOrderDeliveryConfirm,
    LogisticsOrderDispatch,
    LogisticsOrderItemCreate,
    LogisticsPartialDispatchApprovalResult,
    LogisticsPartialDispatchRequestCreate,
    LogisticsPartialDispatchReview,
    LogisticsOrderItemDeliver,
    LogisticsOrderItemLoad,
    LogisticsOrderItemOutcome,
    LogisticsOrderItemUpdate,
    LogisticsOrderOutcomeConfirm,
    LogisticsOrderStockCheckItem,
    LogisticsOrderStockCheckResponse,
    LogisticsOrderStockTransferCreate,
    LogisticsOrderUpdate,
    LogisticsOrderItemAvailability,
    LogisticsOrderWarehouseAvailability,
)

MANAGE_STATUSES = {
    LogisticsOrderStatus.REQUESTED,
    LogisticsOrderStatus.ASSIGNED,
    LogisticsOrderStatus.STOCK_REVIEW,
    LogisticsOrderStatus.INSUFFICIENT_STOCK,
    LogisticsOrderStatus.OBSERVED,
}
ACTIVE_STOCK_RESERVATION_STATUSES = {
    LogisticsOrderStatus.INSUFFICIENT_STOCK,
    LogisticsOrderStatus.RESERVED,
    LogisticsOrderStatus.IN_PREPARATION,
    LogisticsOrderStatus.LOADED,
}
CANCELLABLE_STATUSES = {
    LogisticsOrderStatus.REQUESTED,
    LogisticsOrderStatus.ASSIGNED,
    LogisticsOrderStatus.STOCK_REVIEW,
    LogisticsOrderStatus.INSUFFICIENT_STOCK,
    LogisticsOrderStatus.RESERVED,
    LogisticsOrderStatus.IN_PREPARATION,
    LogisticsOrderStatus.LOADED,
    LogisticsOrderStatus.OBSERVED,
}
ACTIVE_PURCHASE_STATUSES = {
    PurchaseRequestStatus.REQUESTED,
    PurchaseRequestStatus.APPROVED,
    PurchaseRequestStatus.PURCHASED,
    PurchaseRequestStatus.PARTIALLY_RECEIVED,
}


def _load_order_query():
    return select(LogisticsOrder).options(
        selectinload(LogisticsOrder.items),
        selectinload(LogisticsOrder.event),
        selectinload(LogisticsOrder.warehouse),
        selectinload(LogisticsOrder.requester),
        selectinload(LogisticsOrder.assigned_operator),
        selectinload(LogisticsOrder.closer),
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
    if order.status not in MANAGE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido ya avanzo y no se puede editar en su estado actual",
        )
    if any(item.quantity_reserved > 0 for item in order.items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede editar un pedido con stock reservado. Libera la reserva primero.",
        )


def _calculate_total(quantity: Decimal, unit_price: Decimal) -> Decimal:
    return quantity * unit_price


def _available_quantity(stock: StockBalance | None) -> Decimal:
    if not stock:
        return Decimal("0")
    return stock.quantity_on_hand - stock.quantity_reserved - stock.quantity_damaged


def _quantity_to_reserve(requested: Decimal, already_reserved: Decimal, available: Decimal) -> Decimal:
    remaining = max(requested - already_reserved, Decimal("0"))
    return min(remaining, max(available, Decimal("0")))


def _reserved_quantity_from_active_orders(db: Session, warehouse_id: UUID, item_id: UUID) -> Decimal:
    return db.scalar(
        select(func.coalesce(func.sum(LogisticsOrderItem.quantity_reserved), 0))
        .join(LogisticsOrder, LogisticsOrder.id == LogisticsOrderItem.order_id)
        .where(
            LogisticsOrder.warehouse_id == warehouse_id,
            LogisticsOrder.status.in_(ACTIVE_STOCK_RESERVATION_STATUSES),
            LogisticsOrderItem.item_id == item_id,
            LogisticsOrderItem.quantity_reserved > 0,
        )
    ) or Decimal("0")


def _evidence_count(
    db: Session,
    *,
    stage: LogisticsEvidenceStage,
    order_id: UUID | None = None,
    item_id: UUID | None = None,
) -> int:
    filters = [LogisticsEvidence.evidence_stage == stage]
    if order_id:
        filters.append(LogisticsEvidence.logistics_order_id == order_id)
    if item_id:
        filters.append(LogisticsEvidence.logistics_order_item_id == item_id)
    return db.scalar(select(func.count()).select_from(LogisticsEvidence).where(*filters)) or 0


def _require_order_evidence(db: Session, order_id: UUID, stage: LogisticsEvidenceStage, message: str) -> None:
    if _evidence_count(db, order_id=order_id, stage=stage) <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def _sync_stock_reservation_from_orders(
    db: Session,
    *,
    stock: StockBalance,
    user: User,
    order: LogisticsOrder,
) -> StockBalance:
    expected_reserved = _reserved_quantity_from_active_orders(db, stock.warehouse_id, stock.item_id)
    minimum_on_hand = expected_reserved + stock.quantity_damaged
    if stock.quantity_reserved == expected_reserved and stock.quantity_on_hand >= minimum_on_hand:
        return stock

    previous_on_hand = stock.quantity_on_hand
    previous_reserved = stock.quantity_reserved
    previous_damaged = stock.quantity_damaged
    stock.quantity_reserved = expected_reserved
    if stock.quantity_on_hand < minimum_on_hand:
        stock.quantity_on_hand = minimum_on_hand
    stock.updated_at = datetime.utcnow()
    db.add(stock)
    _record_reservation_movement(
        db,
        order=order,
        stock=stock,
        movement_type=StockMovementType.CORRECTION,
        quantity=max(
            abs(stock.quantity_on_hand - previous_on_hand),
            abs(stock.quantity_reserved - previous_reserved),
            Decimal("1"),
        ),
        previous_reserved=previous_reserved,
        new_reserved=stock.quantity_reserved,
        user=user,
        previous_on_hand=previous_on_hand,
        new_on_hand=stock.quantity_on_hand,
        previous_damaged=previous_damaged,
        new_damaged=stock.quantity_damaged,
    )
    return stock


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
    extra_notes: str | None = None,
) -> None:
    reason = (
        f"Reserva pedido logistico {order.title}"
        if movement_type == StockMovementType.RESERVE
        else f"Liberacion reserva pedido logistico {order.title}"
        if movement_type == StockMovementType.UNRESERVE
        else f"Salida de bodega por pedido logistico {order.title}"
        if movement_type == StockMovementType.OUT_TO_EVENT
        else f"Transferencia desde bodega para pedido logistico {order.title}"
        if movement_type == StockMovementType.TRANSFER_OUT
        else f"Transferencia hacia bodega para pedido logistico {order.title}"
        if movement_type == StockMovementType.TRANSFER_IN
        else f"Reparacion de reserva agregada para pedido logistico {order.title}"
    )
    notes = f"Pedido logistico {order.id} - Evento {order.event_id}"
    if extra_notes:
        notes = f"{notes} - {extra_notes}"
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
        if movement_type == StockMovementType.DAMAGE
        else "Correccion de resultado"
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


def _corrected_stock_quantities(
    stock: StockBalance,
    *,
    delta_returned: Decimal,
    delta_returned_damaged: Decimal,
) -> tuple[Decimal, Decimal]:
    target_on_hand = stock.quantity_on_hand + delta_returned + delta_returned_damaged
    target_damaged = stock.quantity_damaged + delta_returned_damaged
    if (
        target_on_hand < 0
        or target_damaged < 0
        or target_on_hand - stock.quantity_reserved - target_damaged < 0
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede corregir la devolucion porque ese stock ya fue reservado o no esta disponible",
        )
    return target_on_hand, target_damaged


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


def _release_order_reservations(db: Session, order: LogisticsOrder, user: User) -> None:
    for order_item in order.items:
        reserved_quantity = order_item.quantity_reserved
        if reserved_quantity > 0:
            stock = _get_stock_balance(
                db,
                warehouse_id=order.warehouse_id,
                item_id=order_item.item_id,
                lock=True,
            )
            if not stock:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock balance not found")
            if order.status in ACTIVE_STOCK_RESERVATION_STATUSES:
                stock = _sync_stock_reservation_from_orders(db, stock=stock, user=user, order=order)
            previous_reserved = stock.quantity_reserved
            new_reserved = previous_reserved - reserved_quantity
            if new_reserved < 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Reserved stock cannot become negative",
                )
            stock.quantity_reserved = new_reserved
            stock.updated_at = datetime.utcnow()
            db.add(stock)
            _record_reservation_movement(
                db,
                order=order,
                stock=stock,
                movement_type=StockMovementType.UNRESERVE,
                quantity=reserved_quantity,
                previous_reserved=previous_reserved,
                new_reserved=new_reserved,
                user=user,
            )

        order_item.quantity_reserved = Decimal("0")
        order_item.quantity_missing = Decimal("0")
        order_item.reservation_status = "PENDING"
        order_item.quantity_loaded = Decimal("0")
        order_item.preparation_status = "PENDING"
        order_item.updated_at = datetime.utcnow()
        db.add(order_item)


def cancel_logistics_order(db: Session, order_id: UUID, user: User) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_manage_order(user, order, db)
    if order.status not in CANCELLABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido ya fue despachado o finalizado y no se puede cancelar",
        )
    active_purchase = db.scalar(
        select(PurchaseRequest.id).where(
            PurchaseRequest.logistics_order_id == order.id,
            PurchaseRequest.status.in_(ACTIVE_PURCHASE_STATUSES),
        )
    )
    if active_purchase:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancela o finaliza primero la solicitud de compra activa asociada al pedido",
        )
    _release_order_reservations(db, order, user)
    order.status = LogisticsOrderStatus.CANCELLED
    order.reserved_at = None
    order.reserved_by = None
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
    repaired_stock = False
    for order_item in order.items:
        inventory_item = db.get(InventoryItem, order_item.item_id)
        stock = _get_stock_balance(
            db,
            warehouse_id=order.warehouse_id,
            item_id=order_item.item_id,
            lock=order.status in ACTIVE_STOCK_RESERVATION_STATUSES,
        )
        if stock and order.status in ACTIVE_STOCK_RESERVATION_STATUSES:
            stock = _sync_stock_reservation_from_orders(db, stock=stock, user=user, order=order)
            repaired_stock = True
        available = _available_quantity(stock) if inventory_item and inventory_item.is_active else Decimal("0")
        covered_quantity = order_item.quantity_reserved + available
        missing = max(order_item.quantity_requested - covered_quantity, Decimal("0"))
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

    if (
        order.status == LogisticsOrderStatus.INSUFFICIENT_STOCK
        and order.items
        and all(item.quantity_reserved == item.quantity_requested and item.quantity_reserved > 0 for item in order.items)
    ):
        order.status = LogisticsOrderStatus.RESERVED
        order.updated_at = datetime.utcnow()
        db.add(order)
        for item in order.items:
            item.quantity_missing = Decimal("0")
            item.reservation_status = "RESERVED"
            item.updated_at = datetime.utcnow()
            db.add(item)
        repaired_stock = True

    if repaired_stock:
        db.commit()

    return LogisticsOrderStockCheckResponse(
        order_id=order.id,
        status=order.status,
        warehouse_id=order.warehouse_id,
        warehouse_name=warehouse.name,
        can_reserve_all=all(item.can_reserve for item in checks) and bool(checks),
        items=checks,
    )


def _operator_warehouse_assignment(db: Session, user_id: UUID, warehouse_id: UUID) -> WarehouseUser | None:
    return db.scalar(
        select(WarehouseUser).where(
            WarehouseUser.user_id == user_id,
            WarehouseUser.warehouse_id == warehouse_id,
        )
    )


def _can_transfer_between_warehouses(
    db: Session,
    *,
    user: User,
    order: LogisticsOrder,
    source_warehouse_id: UUID,
) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role != UserRole.LOGISTICS_OPERATOR or order.assigned_operator_id != user.id:
        return False
    source_assignment = _operator_warehouse_assignment(db, user.id, source_warehouse_id)
    destination_assignment = _operator_warehouse_assignment(db, user.id, order.warehouse_id)
    return bool(
        source_assignment
        and source_assignment.can_view_stock
        and source_assignment.can_manage_stock
        and destination_assignment
        and destination_assignment.can_view_stock
        and destination_assignment.can_manage_stock
        and destination_assignment.can_dispatch_orders
    )


def get_logistics_order_stock_availability(
    db: Session,
    order_id: UUID,
    user: User,
) -> LogisticsOrderAvailabilityResponse:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_review_stock(user, order, db)
    destination = _ensure_active_warehouse(db, order.warehouse_id)

    warehouses = list(
        db.scalars(select(Warehouse).where(Warehouse.is_active.is_(True)).order_by(Warehouse.name.asc())).all()
    )
    if user.role == UserRole.LOGISTICS_OPERATOR:
        assignments = {
            assignment.warehouse_id: assignment
            for assignment in db.scalars(
                select(WarehouseUser).where(
                    WarehouseUser.user_id == user.id,
                    WarehouseUser.can_view_stock.is_(True),
                )
            ).all()
        }
        warehouses = [
            warehouse
            for warehouse in warehouses
            if warehouse.id == order.warehouse_id or warehouse.id in assignments
        ]

    item_ids = [item.item_id for item in order.items]
    warehouse_ids = [warehouse.id for warehouse in warehouses]
    stocks = (
        list(
            db.scalars(
                select(StockBalance).where(
                    StockBalance.item_id.in_(item_ids),
                    StockBalance.warehouse_id.in_(warehouse_ids),
                )
            ).all()
        )
        if item_ids and warehouse_ids
        else []
    )
    stocks_by_key = {(stock.item_id, stock.warehouse_id): stock for stock in stocks}

    items: list[LogisticsOrderItemAvailability] = []
    for order_item in order.items:
        destination_stock = stocks_by_key.get((order_item.item_id, order.warehouse_id))
        destination_available = max(_available_quantity(destination_stock), Decimal("0"))
        missing = max(
            order_item.quantity_requested - order_item.quantity_reserved - destination_available,
            Decimal("0"),
        )
        warehouse_rows: list[LogisticsOrderWarehouseAvailability] = []
        for warehouse in warehouses:
            stock = stocks_by_key.get((order_item.item_id, warehouse.id))
            available = max(_available_quantity(stock), Decimal("0"))
            warehouse_rows.append(
                LogisticsOrderWarehouseAvailability(
                    warehouse_id=warehouse.id,
                    warehouse_name=warehouse.name,
                    is_order_warehouse=warehouse.id == order.warehouse_id,
                    quantity_on_hand=stock.quantity_on_hand if stock else Decimal("0"),
                    quantity_reserved=stock.quantity_reserved if stock else Decimal("0"),
                    quantity_damaged=stock.quantity_damaged if stock else Decimal("0"),
                    available_quantity=available,
                    can_transfer=(
                        warehouse.id != order.warehouse_id
                        and available > 0
                        and missing > 0
                        and _can_transfer_between_warehouses(
                            db,
                            user=user,
                            order=order,
                            source_warehouse_id=warehouse.id,
                        )
                    ),
                )
            )
        items.append(
            LogisticsOrderItemAvailability(
                logistics_order_item_id=order_item.id,
                item_id=order_item.item_id,
                item_name_snapshot=order_item.item_name_snapshot,
                unit_snapshot=order_item.unit_snapshot,
                quantity_requested=order_item.quantity_requested,
                quantity_reserved=order_item.quantity_reserved,
                quantity_missing=missing,
                warehouses=warehouse_rows,
            )
        )

    return LogisticsOrderAvailabilityResponse(
        order_id=order.id,
        warehouse_id=destination.id,
        warehouse_name=destination.name,
        items=items,
    )


def transfer_stock_to_logistics_order(
    db: Session,
    order_id: UUID,
    payload: LogisticsOrderStockTransferCreate,
    user: User,
) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    if order.status not in {
        LogisticsOrderStatus.ASSIGNED,
        LogisticsOrderStatus.STOCK_REVIEW,
        LogisticsOrderStatus.INSUFFICIENT_STOCK,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido no permite transferencias en su estado actual",
        )
    if payload.source_warehouse_id == order.warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La bodega de origen debe ser diferente a la bodega del pedido",
        )
    source_warehouse = _ensure_active_warehouse(db, payload.source_warehouse_id)
    destination_warehouse = _ensure_active_warehouse(db, order.warehouse_id)
    if not _can_transfer_between_warehouses(
        db,
        user=user,
        order=order,
        source_warehouse_id=source_warehouse.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para transferir stock entre estas bodegas",
        )

    order_item = next(
        (item for item in order.items if item.id == payload.logistics_order_item_id),
        None,
    )
    if not order_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logistics order item not found")
    _ensure_active_inventory_item(db, order_item.item_id)

    locked_stocks = list(
        db.scalars(
            select(StockBalance)
            .where(
                StockBalance.item_id == order_item.item_id,
                StockBalance.warehouse_id.in_([source_warehouse.id, destination_warehouse.id]),
            )
            .order_by(StockBalance.warehouse_id.asc())
            .with_for_update()
        ).all()
    )
    stocks_by_warehouse = {stock.warehouse_id: stock for stock in locked_stocks}
    source_stock = stocks_by_warehouse.get(source_warehouse.id)
    if not source_stock:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La bodega de origen no tiene stock del producto")
    source_available = max(_available_quantity(source_stock), Decimal("0"))
    if payload.quantity > source_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Solo hay {source_available} unidades disponibles en {source_warehouse.name}",
        )

    destination_stock = stocks_by_warehouse.get(destination_warehouse.id)
    if not destination_stock:
        destination_stock = StockBalance(
            warehouse_id=destination_warehouse.id,
            item_id=order_item.item_id,
            quantity_on_hand=Decimal("0"),
            quantity_reserved=Decimal("0"),
            quantity_damaged=Decimal("0"),
        )
        db.add(destination_stock)
        db.flush()

    destination_available = max(_available_quantity(destination_stock), Decimal("0"))
    missing = max(
        order_item.quantity_requested - order_item.quantity_reserved - destination_available,
        Decimal("0"),
    )
    if missing <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La bodega del pedido ya tiene stock suficiente para completar este producto",
        )
    if payload.quantity > missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La transferencia no puede superar el faltante actual de {missing}",
        )

    source_previous_on_hand = source_stock.quantity_on_hand
    destination_previous_on_hand = destination_stock.quantity_on_hand
    source_stock.quantity_on_hand -= payload.quantity
    destination_stock.quantity_on_hand += payload.quantity
    source_stock.updated_at = datetime.utcnow()
    destination_stock.updated_at = datetime.utcnow()
    db.add(source_stock)
    db.add(destination_stock)

    transfer_notes = (
        f"{source_warehouse.name} -> {destination_warehouse.name}"
        + (f". {payload.notes}" if payload.notes else "")
    )
    _record_reservation_movement(
        db,
        order=order,
        stock=source_stock,
        movement_type=StockMovementType.TRANSFER_OUT,
        quantity=payload.quantity,
        previous_reserved=source_stock.quantity_reserved,
        new_reserved=source_stock.quantity_reserved,
        user=user,
        previous_on_hand=source_previous_on_hand,
        new_on_hand=source_stock.quantity_on_hand,
        extra_notes=transfer_notes,
    )
    _record_reservation_movement(
        db,
        order=order,
        stock=destination_stock,
        movement_type=StockMovementType.TRANSFER_IN,
        quantity=payload.quantity,
        previous_reserved=destination_stock.quantity_reserved,
        new_reserved=destination_stock.quantity_reserved,
        user=user,
        previous_on_hand=destination_previous_on_hand,
        new_on_hand=destination_stock.quantity_on_hand,
        extra_notes=transfer_notes,
    )

    order_item.quantity_missing = missing - payload.quantity
    order_item.reservation_status = (
        "INSUFFICIENT_STOCK" if order_item.quantity_missing > 0 else "PENDING"
    )
    order_item.updated_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    db.add(order_item)
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def get_partial_dispatch_request(
    db: Session,
    order_id: UUID,
    user: User,
) -> LogisticsPartialDispatchRequest | None:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_view_order(user, order, db)
    return db.scalar(
        select(LogisticsPartialDispatchRequest)
        .where(LogisticsPartialDispatchRequest.order_id == order.id)
        .order_by(LogisticsPartialDispatchRequest.created_at.desc())
        .limit(1)
    )


def create_partial_dispatch_request(
    db: Session,
    order_id: UUID,
    payload: LogisticsPartialDispatchRequestCreate,
    user: User,
) -> LogisticsPartialDispatchRequest:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_view_order(user, order, db)
    if user.role == UserRole.LOGISTICS_OPERATOR:
        _ensure_can_operate_order_warehouse(db, user, order)
    elif user.role == UserRole.SUPERVISOR:
        if not can_manage_event(user, order.event_id, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    elif user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if order.status != LogisticsOrderStatus.INSUFFICIENT_STOCK:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El pedido no tiene una reserva parcial")
    if not any(item.quantity_reserved > 0 for item in order.items) or not any(
        item.quantity_reserved < item.quantity_requested for item in order.items
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El pedido debe tener stock reservado y faltantes")
    active_purchase = db.scalar(
        select(PurchaseRequest.id).where(
            PurchaseRequest.logistics_order_id == order.id,
            PurchaseRequest.status.in_(ACTIVE_PURCHASE_STATUSES),
        )
    )
    if active_purchase:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancela o finaliza la compra activa antes de solicitar un despacho parcial",
        )
    pending = db.scalar(
        select(LogisticsPartialDispatchRequest.id).where(
            LogisticsPartialDispatchRequest.order_id == order.id,
            LogisticsPartialDispatchRequest.status == "PENDING",
        )
    )
    if pending:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una solicitud pendiente")
    request = LogisticsPartialDispatchRequest(
        order_id=order.id,
        status="PENDING",
        reason=payload.reason.strip(),
        requested_by=user.id,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def approve_partial_dispatch_request(
    db: Session,
    request_id: UUID,
    payload: LogisticsPartialDispatchReview,
    user: User,
) -> LogisticsPartialDispatchApprovalResult:
    request = db.get(LogisticsPartialDispatchRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partial dispatch request not found")
    order = get_logistics_order_or_404(db, request.order_id)
    _ensure_can_manage_order(user, order, db)
    if request.status != "PENDING" or order.status != LogisticsOrderStatus.INSUFFICIENT_STOCK:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La solicitud ya no se puede aprobar")

    pending_order = LogisticsOrder(
        parent_order_id=order.id,
        event_id=order.event_id,
        warehouse_id=order.warehouse_id,
        requested_by=order.requested_by,
        assigned_operator_id=order.assigned_operator_id,
        status=LogisticsOrderStatus.ASSIGNED,
        title=f"{order.title[:158]} - Pendiente",
        description=f"Faltantes separados del pedido {order.id}. Motivo: {request.reason}",
        delivery_zone=order.delivery_zone,
        delivery_notes=order.delivery_notes,
    )
    db.add(pending_order)
    db.flush()

    for item in list(order.items):
        missing = item.quantity_requested - item.quantity_reserved
        if missing > 0:
            db.add(
                LogisticsOrderItem(
                    order_id=pending_order.id,
                    item_id=item.item_id,
                    item_name_snapshot=item.item_name_snapshot,
                    item_type_snapshot=item.item_type_snapshot,
                    unit_snapshot=item.unit_snapshot,
                    quantity_requested=missing,
                    unit_price_snapshot=item.unit_price_snapshot,
                    total_price=_calculate_total(missing, item.unit_price_snapshot),
                    notes=f"Pendiente de pedido {order.id}",
                )
            )
        if item.quantity_reserved > 0:
            item.quantity_requested = item.quantity_reserved
            item.quantity_missing = Decimal("0")
            item.reservation_status = "RESERVED"
            item.total_price = _calculate_total(item.quantity_requested, item.unit_price_snapshot)
            item.updated_at = datetime.utcnow()
            db.add(item)
        else:
            db.delete(item)

    db.flush()
    _recalculate_order_total(db, order)
    _recalculate_order_total(db, pending_order)
    order.status = LogisticsOrderStatus.RESERVED
    order.reserved_at = datetime.utcnow()
    order.reserved_by = user.id
    order.updated_at = datetime.utcnow()
    request.status = "APPROVED"
    request.pending_order_id = pending_order.id
    request.reviewed_by = user.id
    request.review_notes = payload.review_notes
    request.reviewed_at = datetime.utcnow()
    request.updated_at = datetime.utcnow()
    db.add(order)
    db.add(request)
    db.commit()
    return LogisticsPartialDispatchApprovalResult(
        request=request,
        dispatch_order=get_logistics_order_or_404(db, order.id),
        pending_order=get_logistics_order_or_404(db, pending_order.id),
    )


def reject_partial_dispatch_request(
    db: Session,
    request_id: UUID,
    payload: LogisticsPartialDispatchReview,
    user: User,
) -> LogisticsPartialDispatchRequest:
    request = db.get(LogisticsPartialDispatchRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partial dispatch request not found")
    order = get_logistics_order_or_404(db, request.order_id)
    _ensure_can_manage_order(user, order, db)
    if request.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La solicitud ya fue revisada")
    request.status = "REJECTED"
    request.reviewed_by = user.id
    request.review_notes = payload.review_notes
    request.reviewed_at = datetime.utcnow()
    request.updated_at = datetime.utcnow()
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def reserve_logistics_order_stock(db: Session, order_id: UUID, user: User) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    if order.status not in {
        LogisticsOrderStatus.ASSIGNED,
        LogisticsOrderStatus.STOCK_REVIEW,
        LogisticsOrderStatus.INSUFFICIENT_STOCK,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido no permite reservar stock en su estado actual",
        )

    warehouse = db.get(Warehouse, order.warehouse_id)
    if not warehouse or not warehouse.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    all_reserved = bool(order.items)
    for order_item in order.items:
        inventory_item = db.get(InventoryItem, order_item.item_id)
        stock = _get_stock_balance(
            db,
            warehouse_id=order.warehouse_id,
            item_id=order_item.item_id,
            lock=True,
        )
        if stock and order.status in ACTIVE_STOCK_RESERVATION_STATUSES:
            stock = _sync_stock_reservation_from_orders(db, stock=stock, user=user, order=order)

        available = _available_quantity(stock) if inventory_item and inventory_item.is_active else Decimal("0")
        reserve_now = _quantity_to_reserve(
            order_item.quantity_requested,
            order_item.quantity_reserved,
            available,
        )
        if stock and reserve_now > 0:
            previous_reserved = stock.quantity_reserved
            new_reserved = previous_reserved + reserve_now
            stock.quantity_reserved = new_reserved
            stock.updated_at = datetime.utcnow()
            order_item.quantity_reserved += reserve_now
            db.add(stock)
            _record_reservation_movement(
                db,
                order=order,
                stock=stock,
                movement_type=StockMovementType.RESERVE,
                quantity=reserve_now,
                previous_reserved=previous_reserved,
                new_reserved=new_reserved,
                user=user,
            )

        missing = max(order_item.quantity_requested - order_item.quantity_reserved, Decimal("0"))
        order_item.quantity_missing = missing
        order_item.reservation_status = "INSUFFICIENT_STOCK" if missing > 0 else "RESERVED"
        order_item.updated_at = datetime.utcnow()
        db.add(order_item)
        all_reserved = all_reserved and missing == 0

    order.status = LogisticsOrderStatus.RESERVED if all_reserved else LogisticsOrderStatus.INSUFFICIENT_STOCK
    order.reserved_at = datetime.utcnow() if all_reserved else None
    order.reserved_by = user.id if all_reserved else None
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return get_logistics_order_or_404(db, order.id)


def unreserve_logistics_order_stock(db: Session, order_id: UUID, user: User) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    if order.status not in ACTIVE_STOCK_RESERVATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido no permite liberar stock en su estado actual",
        )

    reserved_items = [item for item in order.items if item.quantity_reserved > 0]
    if not reserved_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logistics order has no reserved stock")

    _release_order_reservations(db, order, user)

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
    _require_order_evidence(
        db,
        order.id,
        LogisticsEvidenceStage.LOGISTICS_DISPATCH,
        "At least one dispatch evidence is required before confirming warehouse dispatch",
    )

    for order_item in order.items:
        stock = _get_stock_balance(
            db,
            warehouse_id=order.warehouse_id,
            item_id=order_item.item_id,
            lock=True,
        )
        if not stock:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock balance not found")
        stock = _sync_stock_reservation_from_orders(db, stock=stock, user=user, order=order)
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
    _require_order_evidence(
        db,
        order.id,
        LogisticsEvidenceStage.LOGISTICS_DELIVERY,
        "At least one delivery evidence is required before confirming field delivery",
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
    db: Session,
    item_id: UUID,
    payload: LogisticsOrderItemOutcome,
    user: User,
    *,
    commit: bool = True,
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
    if order_item.item_type_snapshot == "RETURNABLE" and payload.quantity_consumed > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RETURNABLE items cannot be marked as consumed",
        )
    if payload.quantity_returned_damaged > 0 and _evidence_count(
        db, item_id=order_item.id, stage=LogisticsEvidenceStage.LOGISTICS_DAMAGED_RETURN
    ) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Damaged returned products require photographic evidence",
        )
    if payload.quantity_lost > 0 and not (payload.notes or "").strip() and _evidence_count(
        db, item_id=order_item.id, stage=LogisticsEvidenceStage.LOGISTICS_LOSS
    ) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lost products require evidence or notes",
        )

    delta_returned = payload.quantity_returned - order_item.quantity_returned
    delta_returned_damaged = payload.quantity_returned_damaged - order_item.quantity_returned_damaged
    if delta_returned != 0 or delta_returned_damaged != 0:
        stock = (
            _get_or_create_stock_balance_for_return(
                db,
                warehouse_id=order.warehouse_id,
                item_id=order_item.item_id,
            )
            if delta_returned > 0 or delta_returned_damaged > 0
            else _get_stock_balance(
                db,
                warehouse_id=order.warehouse_id,
                item_id=order_item.item_id,
                lock=True,
            )
        )
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede corregir la devolucion porque ya no existe el saldo de stock de la bodega",
            )

        _corrected_stock_quantities(
            stock,
            delta_returned=delta_returned,
            delta_returned_damaged=delta_returned_damaged,
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
        elif delta_returned < 0:
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
                movement_type=StockMovementType.CORRECTION,
                quantity=abs(delta_returned),
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
        elif delta_returned_damaged < 0:
            previous_on_hand = stock.quantity_on_hand
            previous_reserved = stock.quantity_reserved
            previous_damaged = stock.quantity_damaged
            stock.quantity_on_hand = previous_on_hand + delta_returned_damaged
            stock.quantity_damaged = previous_damaged + delta_returned_damaged
            stock.updated_at = datetime.utcnow()
            db.add(stock)
            _record_outcome_movement(
                db,
                order=order,
                stock=stock,
                movement_type=StockMovementType.CORRECTION,
                quantity=abs(delta_returned_damaged),
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

    if commit:
        db.commit()
        db.refresh(order_item)
    else:
        db.flush()
    return order_item


def mark_all_consumables_consumed(
    db: Session,
    order_id: UUID,
    user: User,
) -> LogisticsOrder:
    order = get_logistics_order_or_404(db, order_id)
    _ensure_can_reserve_stock(user, order)
    _ensure_can_operate_order_warehouse(db, user, order)
    _ensure_outcome_order_state(order)

    consumables = [
        item
        for item in order.items
        if item.item_type_snapshot == "CONSUMABLE" and item.quantity_delivered > 0
    ]
    if not consumables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este pedido no tiene productos consumibles entregados",
        )

    try:
        for item in consumables:
            register_logistics_order_item_outcome(
                db,
                item.id,
                LogisticsOrderItemOutcome(
                    quantity_consumed=item.quantity_delivered,
                    quantity_returned=Decimal("0"),
                    quantity_returned_damaged=Decimal("0"),
                    quantity_lost=Decimal("0"),
                    quantity_discarded=Decimal("0"),
                    notes=item.outcome_notes,
                ),
                user,
                commit=False,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return get_logistics_order_or_404(db, order_id)


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
