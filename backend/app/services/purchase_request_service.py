from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import (
    Event,
    InventoryItem,
    LogisticsOrder,
    LogisticsOrderItem,
    PurchaseRequest,
    PurchaseRequestItem,
    StockBalance,
    StockMovement,
    User,
    Warehouse,
    WarehouseUser,
)
from app.models.enums import (
    LogisticsOrderStatus,
    PurchaseDeliveryMode,
    PurchaseRequestStatus,
    StockMovementType,
    UserRole,
)
from app.schemas.purchase_request_schema import (
    PurchaseRequestCreate,
    PurchaseRequestFromOrderCreate,
    PurchaseRequestMarkPurchased,
    PurchaseRequestReceive,
    PurchaseRequestReject,
    PurchaseRequestUpdate,
)

ACTIVE_PURCHASE_STATUSES = {
    PurchaseRequestStatus.REQUESTED,
    PurchaseRequestStatus.APPROVED,
    PurchaseRequestStatus.PURCHASED,
    PurchaseRequestStatus.PARTIALLY_RECEIVED,
}


def _load_query():
    return select(PurchaseRequest).options(
        selectinload(PurchaseRequest.items),
        selectinload(PurchaseRequest.event),
        selectinload(PurchaseRequest.logistics_order),
        selectinload(PurchaseRequest.warehouse),
        selectinload(PurchaseRequest.requester),
        selectinload(PurchaseRequest.approver),
        selectinload(PurchaseRequest.purchaser),
        selectinload(PurchaseRequest.receiver),
    )


def get_purchase_request_or_404(db: Session, purchase_request_id: UUID) -> PurchaseRequest:
    purchase = db.scalar(_load_query().where(PurchaseRequest.id == purchase_request_id))
    if not purchase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase request not found")
    return purchase


def _ensure_active_warehouse(db: Session, warehouse_id: UUID) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return warehouse


def _operator_assignment(db: Session, user: User, warehouse_id: UUID) -> WarehouseUser | None:
    if user.role != UserRole.LOGISTICS_OPERATOR:
        return None
    return db.scalar(
        select(WarehouseUser).where(
            WarehouseUser.user_id == user.id,
            WarehouseUser.warehouse_id == warehouse_id,
        )
    )


def _can_manage_purchase_stock(db: Session, user: User, warehouse_id: UUID | None) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.LOGISTICS_OPERATOR and warehouse_id:
        assignment = _operator_assignment(db, user, warehouse_id)
        return bool(assignment and assignment.can_manage_stock)
    return False


def _ensure_can_view_purchase(db: Session, user: User, purchase: PurchaseRequest) -> None:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return
    if user.role in {UserRole.WORKER, UserRole.CLIENT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if user.role == UserRole.SUPERVISOR and purchase.event_id and can_access_event(user, purchase.event_id, db):
        return
    if user.role == UserRole.LOGISTICS_OPERATOR:
        order = purchase.logistics_order or (db.get(LogisticsOrder, purchase.logistics_order_id) if purchase.logistics_order_id else None)
        if order and order.assigned_operator_id == user.id:
            return
        if purchase.warehouse_id:
            assignment = _operator_assignment(db, user, purchase.warehouse_id)
            if assignment and assignment.can_view_stock:
                return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_create_purchase(
    db: Session,
    user: User,
    *,
    event_id: UUID | None,
    logistics_order: LogisticsOrder | None,
) -> None:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return
    if user.role == UserRole.SUPERVISOR and event_id and can_manage_event(user, event_id, db):
        return
    if user.role == UserRole.LOGISTICS_OPERATOR and logistics_order and logistics_order.assigned_operator_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_admin(user: User) -> None:
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _recalculate_totals(purchase: PurchaseRequest) -> None:
    purchase.total_estimated_amount = sum((item.total_estimated for item in purchase.items), Decimal("0"))
    purchase.total_purchased_amount = sum((item.total_purchased for item in purchase.items), Decimal("0"))


def _item_by_id(purchase: PurchaseRequest) -> dict[UUID, PurchaseRequestItem]:
    return {item.id: item for item in purchase.items}


def _active_purchase_for_order(db: Session, order_id: UUID) -> PurchaseRequest | None:
    return db.scalar(
        select(PurchaseRequest)
        .where(
            PurchaseRequest.logistics_order_id == order_id,
            PurchaseRequest.status.in_(ACTIVE_PURCHASE_STATUSES),
        )
        .order_by(PurchaseRequest.created_at.desc())
        .limit(1)
    )


def _receive_status(purchase: PurchaseRequest) -> PurchaseRequestStatus:
    requested = sum((item.quantity_requested for item in purchase.items), Decimal("0"))
    received = sum((item.quantity_received for item in purchase.items), Decimal("0"))
    if received >= requested:
        return PurchaseRequestStatus.RECEIVED
    return PurchaseRequestStatus.PARTIALLY_RECEIVED


def _create_purchase_in_movement(
    db: Session,
    *,
    warehouse_id: UUID,
    item_id: UUID,
    quantity: Decimal,
    user: User,
    purchase_request_id: UUID,
    notes: str | None,
) -> None:
    stock = db.scalar(
        select(StockBalance)
        .where(StockBalance.warehouse_id == warehouse_id, StockBalance.item_id == item_id)
        .with_for_update()
    )
    if not stock:
        stock = StockBalance(
            warehouse_id=warehouse_id,
            item_id=item_id,
            quantity_on_hand=Decimal("0"),
            quantity_reserved=Decimal("0"),
            quantity_damaged=Decimal("0"),
        )
        db.add(stock)
        db.flush()

    previous_on_hand = stock.quantity_on_hand
    previous_reserved = stock.quantity_reserved
    previous_damaged = stock.quantity_damaged
    stock.quantity_on_hand = previous_on_hand + quantity
    stock.updated_at = datetime.utcnow()
    db.add(stock)
    db.add(
        StockMovement(
            warehouse_id=warehouse_id,
            item_id=item_id,
            stock_balance_id=stock.id,
            movement_type=StockMovementType.PURCHASE_IN,
            quantity=quantity,
            previous_quantity_on_hand=previous_on_hand,
            new_quantity_on_hand=stock.quantity_on_hand,
            previous_quantity_reserved=previous_reserved,
            new_quantity_reserved=previous_reserved,
            previous_quantity_damaged=previous_damaged,
            new_quantity_damaged=previous_damaged,
            reference_type="PURCHASE_REQUEST",
            reference_id=purchase_request_id,
            reason="Ingreso por compra",
            notes=notes,
            created_by=user.id,
        )
    )


def _available_quantity(stock: StockBalance | None) -> Decimal:
    if not stock:
        return Decimal("0")
    available = stock.quantity_on_hand - stock.quantity_reserved - stock.quantity_damaged
    return max(available, Decimal("0"))


def create_purchase_request(db: Session, payload: PurchaseRequestCreate, user: User) -> PurchaseRequest:
    logistics_order = db.get(LogisticsOrder, payload.logistics_order_id) if payload.logistics_order_id else None
    if payload.logistics_order_id and not logistics_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logistics order not found")
    event_id = payload.event_id or (logistics_order.event_id if logistics_order else None)
    if event_id and not db.get(Event, event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    _ensure_can_create_purchase(db, user, event_id=event_id, logistics_order=logistics_order)
    if payload.delivery_mode == PurchaseDeliveryMode.TO_WAREHOUSE:
        _ensure_active_warehouse(db, payload.warehouse_id)  # type: ignore[arg-type]

    purchase = PurchaseRequest(
        event_id=event_id,
        logistics_order_id=payload.logistics_order_id,
        warehouse_id=payload.warehouse_id,
        requested_by=user.id,
        delivery_mode=payload.delivery_mode,
        title=payload.title.strip(),
        description=_clean_text(payload.description),
        notes=_clean_text(payload.notes),
    )
    db.add(purchase)
    db.flush()
    total_estimated = Decimal("0")
    for row in payload.items:
        item = db.get(InventoryItem, row.item_id)
        if not item or not item.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
        total = row.quantity_requested * row.unit_price_estimated
        total_estimated += total
        db.add(
            PurchaseRequestItem(
                purchase_request_id=purchase.id,
                item_id=item.id,
                item_name_snapshot=item.name,
                unit_snapshot=item.unit,
                quantity_requested=row.quantity_requested,
                unit_price_estimated=row.unit_price_estimated,
                total_estimated=total,
                notes=_clean_text(row.notes),
            )
        )
    db.flush()
    purchase.total_estimated_amount = total_estimated
    purchase.total_purchased_amount = Decimal("0")
    db.add(purchase)
    db.commit()
    return get_purchase_request_or_404(db, purchase.id)


def create_purchase_request_from_order(
    db: Session, order_id: UUID, payload: PurchaseRequestFromOrderCreate, user: User
) -> PurchaseRequest:
    order = db.scalar(
        select(LogisticsOrder).options(selectinload(LogisticsOrder.items)).where(LogisticsOrder.id == order_id)
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logistics order not found")
    _ensure_can_create_purchase(db, user, event_id=order.event_id, logistics_order=order)
    active_purchase = _active_purchase_for_order(db, order.id)
    if active_purchase:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This logistics order already has an active purchase request. "
                "Finish, reject or cancel it before creating another one."
            ),
        )
    if payload.delivery_mode == PurchaseDeliveryMode.TO_WAREHOUSE:
        _ensure_active_warehouse(db, payload.warehouse_id)  # type: ignore[arg-type]

    missing_items: list[tuple[LogisticsOrderItem, Decimal]] = []
    for order_item in order.items:
        stock = db.scalar(
            select(StockBalance).where(
                StockBalance.warehouse_id == order.warehouse_id,
                StockBalance.item_id == order_item.item_id,
            )
        )
        inventory_item = db.get(InventoryItem, order_item.item_id)
        available = _available_quantity(stock) if inventory_item and inventory_item.is_active else Decimal("0")
        covered_quantity = order_item.quantity_reserved + available
        missing = max(order_item.quantity_requested - covered_quantity, Decimal("0"))
        order_item.quantity_missing = missing
        order_item.reservation_status = "INSUFFICIENT_STOCK" if missing > 0 else "PENDING"
        order_item.updated_at = datetime.utcnow()
        db.add(order_item)
        if missing > 0:
            missing_items.append((order_item, missing))
    if not missing_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No missing items to purchase")
    order.status = LogisticsOrderStatus.INSUFFICIENT_STOCK
    order.updated_at = datetime.utcnow()
    db.add(order)

    purchase = PurchaseRequest(
        event_id=order.event_id,
        logistics_order_id=order.id,
        warehouse_id=payload.warehouse_id,
        requested_by=user.id,
        delivery_mode=payload.delivery_mode,
        title=payload.title.strip(),
        notes=_clean_text(payload.notes),
    )
    db.add(purchase)
    db.flush()
    total_estimated = Decimal("0")
    for order_item, missing in missing_items:
        inventory_item = db.get(InventoryItem, order_item.item_id)
        estimated_price = inventory_item.unit_price if inventory_item else order_item.unit_price_snapshot
        total = missing * estimated_price
        total_estimated += total
        db.add(
            PurchaseRequestItem(
                purchase_request_id=purchase.id,
                logistics_order_item_id=order_item.id,
                item_id=order_item.item_id,
                item_name_snapshot=order_item.item_name_snapshot,
                unit_snapshot=order_item.unit_snapshot,
                quantity_requested=missing,
                unit_price_estimated=estimated_price,
                total_estimated=total,
                notes="Faltante para pedido logistico",
            )
        )
    db.flush()
    purchase.total_estimated_amount = total_estimated
    purchase.total_purchased_amount = Decimal("0")
    db.add(purchase)
    db.commit()
    return get_purchase_request_or_404(db, purchase.id)


def list_purchase_requests(
    db: Session,
    *,
    user: User,
    status_filter: PurchaseRequestStatus | None,
    delivery_mode: PurchaseDeliveryMode | None,
    event_id: UUID | None,
    logistics_order_id: UUID | None,
    warehouse_id: UUID | None,
    q: str | None,
    page: int,
    limit: int,
) -> tuple[list[PurchaseRequest], int]:
    if user.role in {UserRole.WORKER, UserRole.CLIENT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    filters = []
    if status_filter:
        filters.append(PurchaseRequest.status == status_filter)
    if delivery_mode:
        filters.append(PurchaseRequest.delivery_mode == delivery_mode)
    if event_id:
        filters.append(PurchaseRequest.event_id == event_id)
    if logistics_order_id:
        filters.append(PurchaseRequest.logistics_order_id == logistics_order_id)
    if warehouse_id:
        filters.append(PurchaseRequest.warehouse_id == warehouse_id)
    if q:
        pattern = f"%{q}%"
        filters.append(or_(PurchaseRequest.title.ilike(pattern), PurchaseRequest.notes.ilike(pattern)))

    statement = _load_query().where(*filters).order_by(PurchaseRequest.created_at.desc())
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        total = db.scalar(select(func.count()).select_from(PurchaseRequest).where(*filters)) or 0
        items = list(db.scalars(statement.offset((page - 1) * limit).limit(limit)).all())
        return items, total

    all_items = list(db.scalars(statement).all())
    visible = []
    for purchase in all_items:
        try:
            _ensure_can_view_purchase(db, user, purchase)
            visible.append(purchase)
        except HTTPException:
            continue
    return visible[(page - 1) * limit : (page - 1) * limit + limit], len(visible)


def get_purchase_request_detail(db: Session, purchase_request_id: UUID, user: User) -> PurchaseRequest:
    purchase = get_purchase_request_or_404(db, purchase_request_id)
    _ensure_can_view_purchase(db, user, purchase)
    return purchase


def update_purchase_request(db: Session, purchase_request_id: UUID, payload: PurchaseRequestUpdate, user: User) -> PurchaseRequest:
    _ensure_admin(user)
    purchase = get_purchase_request_or_404(db, purchase_request_id)
    if purchase.status not in {PurchaseRequestStatus.REQUESTED, PurchaseRequestStatus.APPROVED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase request cannot be edited")
    data = payload.model_dump(exclude_unset=True)
    if "warehouse_id" in data and data["warehouse_id"] is not None:
        _ensure_active_warehouse(db, data["warehouse_id"])
    for field, value in data.items():
        setattr(purchase, field, _clean_text(value) if isinstance(value, str) else value)
    purchase.updated_at = datetime.utcnow()
    db.add(purchase)
    db.commit()
    return get_purchase_request_or_404(db, purchase.id)


def approve_purchase_request(db: Session, purchase_request_id: UUID, user: User) -> PurchaseRequest:
    _ensure_admin(user)
    purchase = get_purchase_request_or_404(db, purchase_request_id)
    if purchase.status != PurchaseRequestStatus.REQUESTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase request must be REQUESTED")
    purchase.status = PurchaseRequestStatus.APPROVED
    purchase.approved_by = user.id
    purchase.approved_at = datetime.utcnow()
    purchase.updated_at = datetime.utcnow()
    db.add(purchase)
    db.commit()
    return get_purchase_request_or_404(db, purchase.id)


def reject_purchase_request(
    db: Session, purchase_request_id: UUID, payload: PurchaseRequestReject, user: User
) -> PurchaseRequest:
    _ensure_admin(user)
    purchase = get_purchase_request_or_404(db, purchase_request_id)
    if purchase.status not in {PurchaseRequestStatus.REQUESTED, PurchaseRequestStatus.APPROVED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase request cannot be rejected")
    purchase.status = PurchaseRequestStatus.REJECTED
    purchase.rejection_reason = payload.rejection_reason.strip()
    purchase.rejected_at = datetime.utcnow()
    purchase.updated_at = datetime.utcnow()
    db.add(purchase)
    db.commit()
    return get_purchase_request_or_404(db, purchase.id)


def mark_purchase_request_purchased(
    db: Session, purchase_request_id: UUID, payload: PurchaseRequestMarkPurchased, user: User
) -> PurchaseRequest:
    purchase = get_purchase_request_or_404(db, purchase_request_id)
    if not _can_manage_purchase_stock(db, user, purchase.warehouse_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if purchase.status != PurchaseRequestStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase request must be APPROVED")
    items_by_id = _item_by_id(purchase)
    for row in payload.items:
        item = items_by_id.get(row.purchase_request_item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase request item not found")
        if row.quantity_purchased > item.quantity_requested:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity_purchased cannot exceed requested")
        item.quantity_purchased = row.quantity_purchased
        item.unit_price_purchased = row.unit_price_purchased
        item.total_purchased = row.quantity_purchased * row.unit_price_purchased
        item.updated_at = datetime.utcnow()
        db.add(item)
    purchase.status = PurchaseRequestStatus.PURCHASED
    purchase.purchased_by = user.id
    purchase.purchased_at = datetime.utcnow()
    purchase.notes = _clean_text(payload.notes) or purchase.notes
    purchase.updated_at = datetime.utcnow()
    _recalculate_totals(purchase)
    db.add(purchase)
    db.commit()
    return get_purchase_request_or_404(db, purchase.id)


def receive_purchase_request(
    db: Session, purchase_request_id: UUID, payload: PurchaseRequestReceive, user: User
) -> PurchaseRequest:
    purchase = get_purchase_request_or_404(db, purchase_request_id)
    if purchase.delivery_mode != PurchaseDeliveryMode.TO_WAREHOUSE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase is not TO_WAREHOUSE")
    if not purchase.warehouse_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="warehouse_id is required")
    _ensure_active_warehouse(db, purchase.warehouse_id)
    if not _can_manage_purchase_stock(db, user, purchase.warehouse_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if purchase.status not in {
        PurchaseRequestStatus.APPROVED,
        PurchaseRequestStatus.PURCHASED,
        PurchaseRequestStatus.PARTIALLY_RECEIVED,
    }:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase request cannot be received")
    items_by_id = _item_by_id(purchase)
    for row in payload.items:
        item = items_by_id.get(row.purchase_request_item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase request item not found")
        max_receive = item.quantity_purchased if item.quantity_purchased > 0 else item.quantity_requested
        if item.quantity_received + row.quantity_received > max_receive:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity_received exceeds purchased")
        item.quantity_received += row.quantity_received
        item.updated_at = datetime.utcnow()
        db.add(item)
        _create_purchase_in_movement(
            db,
            warehouse_id=purchase.warehouse_id,
            item_id=item.item_id,
            quantity=row.quantity_received,
            user=user,
            purchase_request_id=purchase.id,
            notes=_clean_text(payload.notes),
        )
    purchase.status = _receive_status(purchase)
    purchase.received_by = user.id
    purchase.received_at = datetime.utcnow()
    purchase.notes = _clean_text(payload.notes) or purchase.notes
    purchase.updated_at = datetime.utcnow()
    db.add(purchase)
    db.commit()
    return get_purchase_request_or_404(db, purchase.id)


def deliver_direct_to_event(
    db: Session, purchase_request_id: UUID, payload: PurchaseRequestReceive, user: User
) -> PurchaseRequest:
    purchase = get_purchase_request_or_404(db, purchase_request_id)
    if purchase.delivery_mode != PurchaseDeliveryMode.DIRECT_TO_EVENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase is not DIRECT_TO_EVENT")
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.LOGISTICS_OPERATOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    _ensure_can_view_purchase(db, user, purchase)
    if purchase.status not in {PurchaseRequestStatus.APPROVED, PurchaseRequestStatus.PURCHASED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase request cannot be delivered")
    items_by_id = _item_by_id(purchase)
    for row in payload.items:
        item = items_by_id.get(row.purchase_request_item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase request item not found")
        max_receive = item.quantity_purchased if item.quantity_purchased > 0 else item.quantity_requested
        if item.quantity_received + row.quantity_received > max_receive:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity_received exceeds purchased")
        item.quantity_received += row.quantity_received
        item.updated_at = datetime.utcnow()
        db.add(item)
    purchase.status = PurchaseRequestStatus.DELIVERED_DIRECT_TO_EVENT
    purchase.received_by = user.id
    purchase.received_at = datetime.utcnow()
    purchase.notes = _clean_text(payload.notes) or purchase.notes
    purchase.updated_at = datetime.utcnow()
    db.add(purchase)
    db.commit()
    return get_purchase_request_or_404(db, purchase.id)


def cancel_purchase_request(db: Session, purchase_request_id: UUID, user: User) -> PurchaseRequest:
    purchase = get_purchase_request_or_404(db, purchase_request_id)
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN} and not (
        user.id == purchase.requested_by and purchase.status == PurchaseRequestStatus.REQUESTED
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if purchase.status not in ACTIVE_PURCHASE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase request cannot be cancelled")
    purchase.status = PurchaseRequestStatus.CANCELLED
    purchase.cancelled_at = datetime.utcnow()
    purchase.updated_at = datetime.utcnow()
    db.add(purchase)
    db.commit()
    return get_purchase_request_or_404(db, purchase.id)
