from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import (
    can_access_event,
    can_access_order,
    can_create_logistics_order,
    can_complete_order_item_stage,
    can_manage_event,
    can_manage_order,
    can_upload_order_evidence,
    can_view_order_evidence,
)
from app.models.core import (
    CatalogItem,
    Event,
    EventOrder,
    EventOrderItem,
    EventStaff,
    EventZone,
    OrderEvidence,
    User,
)
from app.models.enums import OrderEvidenceStage, OrderItemStageStatus, OrderStatus, UserRole
from app.schemas.order_schema import (
    CatalogItemCreate,
    CatalogItemUpdate,
    EventOrderCreate,
    EventOrderItemCreate,
    EventOrderItemUpdate,
    EventOrderStatusUpdate,
    EventOrderUpdate,
    OrderEvidenceCreate,
    OrderItemStageUpdate,
)
from app.services.file_storage_service import delete_stored_file, save_order_evidence_file

TERMINAL_ORDER_STATUSES = {OrderStatus.CLOSED, OrderStatus.CANCELLED}
LOGISTICS_ORDER_ROLES = {
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.SUPERVISOR,
    UserRole.LOGISTICS_OPERATOR,
}
STAGE_FOLDERS = {
    OrderEvidenceStage.LOAD: "load",
    OrderEvidenceStage.DELIVERY: "delivery",
    OrderEvidenceStage.RETURN: "return",
}


def get_catalog_item_or_404(db: Session, item_id: UUID) -> CatalogItem:
    item = db.get(CatalogItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")
    return item


def list_catalog_items(
    db: Session,
    *,
    q: str | None,
    category: str | None,
    is_active: bool | None,
    page: int,
    limit: int,
) -> tuple[list[CatalogItem], int]:
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                CatalogItem.name.ilike(pattern),
                CatalogItem.category.ilike(pattern),
                CatalogItem.description.ilike(pattern),
            )
        )
    if category:
        filters.append(CatalogItem.category == category)
    if is_active is not None:
        filters.append(CatalogItem.is_active == is_active)

    total = db.scalar(select(func.count()).select_from(CatalogItem).where(*filters)) or 0
    items = list(
        db.scalars(
            select(CatalogItem)
            .where(*filters)
            .order_by(CatalogItem.name.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def create_catalog_item(db: Session, payload: CatalogItemCreate) -> CatalogItem:
    data = payload.model_dump()
    if not data.get("name"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    item = CatalogItem(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_catalog_item(db: Session, item_id: UUID, payload: CatalogItemUpdate) -> CatalogItem:
    item = get_catalog_item_or_404(db, item_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(item, field, value)
    item.updated_at = datetime.utcnow()
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def deactivate_catalog_item(db: Session, item_id: UUID) -> CatalogItem:
    item = get_catalog_item_or_404(db, item_id)
    item.is_active = False
    item.updated_at = datetime.utcnow()
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_order_or_404(db: Session, order_id: UUID) -> EventOrder:
    order = db.get(EventOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def get_order_item_or_404(db: Session, item_id: UUID) -> EventOrderItem:
    item = db.get(EventOrderItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
    return item


def ensure_can_access_order(db: Session, user: User, order_id: UUID) -> EventOrder:
    order = get_order_or_404(db, order_id)
    if not can_access_order(user, order_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return order


def ensure_can_manage_order(db: Session, user: User, order_id: UUID) -> EventOrder:
    order = get_order_or_404(db, order_id)
    if not can_manage_order(user, order_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return order


def _ensure_event_access(db: Session, user: User, event_id: UUID, *, manage: bool = False) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    allowed = can_manage_event(user, event_id, db) if manage else can_access_event(user, event_id, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return event


def _ensure_can_create_logistics_order(db: Session, user: User, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if not can_create_logistics_order(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return event


def _ensure_order_mutable(order: EventOrder, user: User) -> None:
    if order.status in TERMINAL_ORDER_STATUSES and user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify closed or cancelled orders",
        )


def _validate_assignee(db: Session, event_id: UUID, user_id: UUID | None) -> None:
    if user_id is None:
        return
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
    if user.role not in {UserRole.SUPERVISOR, UserRole.LOGISTICS_OPERATOR}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned user must be supervisor or logistics operator",
        )
    assigned = db.scalar(
        select(EventStaff.id).where(EventStaff.event_id == event_id, EventStaff.user_id == user_id)
    )
    if assigned is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned user must belong to event staff",
        )


def _validate_zone(db: Session, order: EventOrder, zone_id: UUID | None) -> None:
    if zone_id is None:
        return
    zone = db.get(EventZone, zone_id)
    if not zone or zone.event_id != order.event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="zone_id must belong to the order event",
        )


def _apply_progress(order: EventOrder) -> EventOrder:
    items = list(getattr(order, "items", []) or [])
    total = len(items)
    loaded = sum(1 for item in items if item.load_status == OrderItemStageStatus.COMPLETED)
    delivered = sum(1 for item in items if item.delivery_status == OrderItemStageStatus.COMPLETED)
    returned = sum(1 for item in items if item.return_status == OrderItemStageStatus.COMPLETED)
    progress = {
        "total_items": total,
        "loaded_items": loaded,
        "delivered_items": delivered,
        "returned_items": returned,
        "load_progress_percentage": round((loaded / total) * 100) if total else 0,
        "delivery_progress_percentage": round((delivered / total) * 100) if total else 0,
        "return_progress_percentage": round((returned / total) * 100) if total else 0,
    }
    setattr(order, "progress", progress)
    return order


def _load_order_query():
    return select(EventOrder).options(
        selectinload(EventOrder.items),
        selectinload(EventOrder.assignee),
        selectinload(EventOrder.event).selectinload(Event.client),
    )


def _refresh_order_with_progress(db: Session, order_id: UUID) -> EventOrder:
    order = db.scalar(_load_order_query().where(EventOrder.id == order_id))
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return _apply_progress(order)


def _recalculate_order_total(db: Session, order: EventOrder) -> None:
    total = db.scalar(
        select(func.coalesce(func.sum(EventOrderItem.total_price), 0)).where(
            EventOrderItem.order_id == order.id
        )
    )
    order.total_amount = Decimal(total or 0)
    order.updated_at = datetime.utcnow()
    db.add(order)


def _calculate_item_total(quantity: Decimal, unit_price: Decimal | None) -> Decimal:
    return quantity * (unit_price or Decimal("0"))


def create_order(db: Session, event_id: UUID, payload: EventOrderCreate, user: User) -> EventOrder:
    _ensure_can_create_logistics_order(db, user, event_id)
    _validate_assignee(db, event_id, payload.assigned_to)
    order = EventOrder(
        event_id=event_id,
        requested_by=user.id,
        status=OrderStatus.DRAFT,
        **payload.model_dump(),
    )
    db.add(order)
    db.commit()
    return _refresh_order_with_progress(db, order.id)


def list_event_orders(
    db: Session,
    *,
    event_id: UUID,
    user: User,
    status_filter: OrderStatus | None,
    assigned_to: UUID | None,
    page: int,
    limit: int,
) -> tuple[list[EventOrder], int]:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if user.role == UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if user.role != UserRole.LOGISTICS_OPERATOR:
        _ensure_event_access(db, user, event_id)
    filters = [EventOrder.event_id == event_id]
    if user.role == UserRole.LOGISTICS_OPERATOR:
        filters.append(EventOrder.assigned_to == user.id)
    if status_filter is not None:
        filters.append(EventOrder.status == status_filter)
    if assigned_to is not None:
        filters.append(EventOrder.assigned_to == assigned_to)

    total = db.scalar(select(func.count()).select_from(EventOrder).where(*filters)) or 0
    orders = list(
        db.scalars(
            _load_order_query()
            .where(*filters)
            .order_by(EventOrder.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return [_apply_progress(order) for order in orders], total


def list_my_orders(db: Session, *, user: User, page: int, limit: int) -> tuple[list[EventOrder], int]:
    if user.role not in LOGISTICS_ORDER_ROLES:
        return [], 0
    filters = [EventOrder.assigned_to == user.id]
    total = db.scalar(select(func.count()).select_from(EventOrder).where(*filters)) or 0
    orders = list(
        db.scalars(
            _load_order_query()
            .where(*filters)
            .order_by(EventOrder.required_date.asc().nullslast(), EventOrder.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return [_apply_progress(order) for order in orders], total


def get_order_detail(db: Session, order_id: UUID, user: User) -> EventOrder:
    ensure_can_access_order(db, user, order_id)
    return _refresh_order_with_progress(db, order_id)


def update_order(db: Session, order_id: UUID, payload: EventOrderUpdate, user: User) -> EventOrder:
    order = ensure_can_manage_order(db, user, order_id)
    _ensure_order_mutable(order, user)
    data = payload.model_dump(exclude_unset=True)
    if "assigned_to" in data:
        _validate_assignee(db, order.event_id, data["assigned_to"])
    for field, value in data.items():
        setattr(order, field, value)
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return _refresh_order_with_progress(db, order.id)


def update_order_status(
    db: Session, order_id: UUID, payload: EventOrderStatusUpdate, user: User
) -> EventOrder:
    order = ensure_can_manage_order(db, user, order_id)
    if order.status in TERMINAL_ORDER_STATUSES and user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update closed or cancelled orders",
        )
    order.status = payload.status
    if payload.status == OrderStatus.CLOSED:
        order.closed_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return _refresh_order_with_progress(db, order.id)


def cancel_order(db: Session, order_id: UUID, user: User) -> EventOrder:
    order = ensure_can_manage_order(db, user, order_id)
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return _refresh_order_with_progress(db, order.id)


def create_order_item(
    db: Session, order_id: UUID, payload: EventOrderItemCreate, user: User
) -> EventOrderItem:
    order = ensure_can_manage_order(db, user, order_id)
    _ensure_order_mutable(order, user)
    _validate_zone(db, order, payload.zone_id)

    catalog_item = None
    if payload.catalog_item_id:
        catalog_item = get_catalog_item_or_404(db, payload.catalog_item_id)
        if not catalog_item.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Catalog item is inactive"
            )
    name = payload.item_name_snapshot or (catalog_item.name if catalog_item else None)
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item name is required")
    unit_price = payload.unit_price
    if unit_price is None and catalog_item:
        unit_price = catalog_item.default_unit_price or Decimal("0")
    if unit_price is None:
        unit_price = Decimal("0")
    unit = payload.unit or (catalog_item.unit if catalog_item else None)
    item = EventOrderItem(
        order_id=order_id,
        catalog_item_id=payload.catalog_item_id,
        zone_id=payload.zone_id,
        item_name_snapshot=name,
        quantity=payload.quantity,
        unit=unit,
        unit_price=unit_price,
        total_price=_calculate_item_total(payload.quantity, unit_price),
        notes=payload.notes,
    )
    db.add(item)
    db.flush()
    _recalculate_order_total(db, order)
    db.commit()
    db.refresh(item)
    return item


def update_order_item(
    db: Session, order_id: UUID, item_id: UUID, payload: EventOrderItemUpdate, user: User
) -> EventOrderItem:
    order = ensure_can_manage_order(db, user, order_id)
    _ensure_order_mutable(order, user)
    item = get_order_item_or_404(db, item_id)
    if item.order_id != order_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
    data = payload.model_dump(exclude_unset=True)
    catalog_item = None
    if "catalog_item_id" in data and data["catalog_item_id"] is not None:
        catalog_item = get_catalog_item_or_404(db, data["catalog_item_id"])
        if not catalog_item.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Catalog item is inactive"
            )
        data.setdefault("item_name_snapshot", catalog_item.name)
        data.setdefault("unit", catalog_item.unit)
        data.setdefault("unit_price", catalog_item.default_unit_price or Decimal("0"))
    if "zone_id" in data:
        _validate_zone(db, order, data["zone_id"])
    for field, value in data.items():
        setattr(item, field, value)
    item.total_price = _calculate_item_total(item.quantity, item.unit_price)
    item.updated_at = datetime.utcnow()
    db.add(item)
    _recalculate_order_total(db, order)
    db.commit()
    db.refresh(item)
    return item


def delete_order_item(db: Session, order_id: UUID, item_id: UUID, user: User) -> None:
    order = ensure_can_manage_order(db, user, order_id)
    _ensure_order_mutable(order, user)
    item = get_order_item_or_404(db, item_id)
    if item.order_id != order_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
    db.delete(item)
    db.flush()
    _recalculate_order_total(db, order)
    db.commit()


def _auto_update_order_status(order: EventOrder) -> None:
    items = list(order.items or [])
    if not items:
        return
    if all(item.return_status == OrderItemStageStatus.COMPLETED for item in items):
        order.status = OrderStatus.RETURNED
    elif all(item.delivery_status == OrderItemStageStatus.COMPLETED for item in items):
        order.status = OrderStatus.DELIVERED
    elif all(item.load_status == OrderItemStageStatus.COMPLETED for item in items):
        order.status = OrderStatus.LOADED


def update_item_stage(
    db: Session,
    item_id: UUID,
    payload: OrderItemStageUpdate,
    user: User,
    *,
    stage: OrderEvidenceStage,
) -> EventOrderItem:
    item = get_order_item_or_404(db, item_id)
    order = ensure_can_access_order(db, user, item.order_id)
    if not can_complete_order_item_stage(user, item_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    _ensure_order_mutable(order, user)
    if payload.status == OrderItemStageStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage status must be COMPLETED or OBSERVED",
        )
    if (
        stage == OrderEvidenceStage.DELIVERY
        and item.load_status == OrderItemStageStatus.PENDING
        and user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item must be loaded first")
    if (
        stage == OrderEvidenceStage.RETURN
        and item.delivery_status == OrderItemStageStatus.PENDING
        and user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Item must be delivered first"
        )

    now = datetime.utcnow()
    if stage == OrderEvidenceStage.LOAD:
        item.load_status = payload.status
        item.loaded_at = now
        item.loaded_by = user.id
        item.load_observation = payload.observation
    elif stage == OrderEvidenceStage.DELIVERY:
        item.delivery_status = payload.status
        item.delivered_at = now
        item.delivered_by = user.id
        item.delivery_observation = payload.observation
    else:
        item.return_status = payload.status
        item.returned_at = now
        item.returned_by = user.id
        item.return_observation = payload.observation
    item.updated_at = now
    db.add(item)

    order = db.scalar(select(EventOrder).options(selectinload(EventOrder.items)).where(EventOrder.id == item.order_id))
    if order:
        _auto_update_order_status(order)
        order.updated_at = now
        db.add(order)
    db.commit()
    return item


def create_order_evidence(
    db: Session, order_id: UUID, payload: OrderEvidenceCreate, file: UploadFile, user: User
) -> OrderEvidence:
    order = ensure_can_access_order(db, user, order_id)
    if not can_upload_order_evidence(user, order_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    _ensure_order_mutable(order, user)
    if payload.order_item_id:
        item = get_order_item_or_404(db, payload.order_item_id)
        if item.order_id != order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="order_item_id must belong to the order",
            )

    stage_folder = STAGE_FOLDERS[payload.stage]
    if payload.order_item_id:
        folder = f"events/{order.event_id}/orders/{order.id}/items/{payload.order_item_id}/{stage_folder}"
    else:
        folder = f"events/{order.event_id}/orders/{order.id}/{stage_folder}"
    file_url, file_type, file_size = save_order_evidence_file(folder, file)
    evidence = OrderEvidence(
        event_id=order.event_id,
        order_id=order_id,
        order_item_id=payload.order_item_id,
        uploaded_by=user.id,
        stage=payload.stage,
        file_url=file_url,
        file_type=file_type,
        file_name=file.filename,
        file_size=file_size,
        description=payload.description,
        visible_to_client=payload.visible_to_client,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def list_order_evidences(
    db: Session,
    *,
    order_id: UUID,
    user: User,
    stage: OrderEvidenceStage | None,
    order_item_id: UUID | None,
) -> list[OrderEvidence]:
    ensure_can_access_order(db, user, order_id)
    filters = [OrderEvidence.order_id == order_id]
    if user.role == UserRole.CLIENT:
        filters.append(OrderEvidence.visible_to_client.is_(True))
    if stage:
        filters.append(OrderEvidence.stage == stage)
    if order_item_id:
        filters.append(OrderEvidence.order_item_id == order_item_id)
    return list(
        db.scalars(
            select(OrderEvidence).where(*filters).order_by(OrderEvidence.created_at.desc())
        ).all()
    )


def delete_order_evidence(db: Session, evidence_id: UUID, user: User) -> None:
    evidence = db.get(OrderEvidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    if not can_view_order_evidence(user, evidence_id, db) or user.role == UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    order = get_order_or_404(db, evidence.order_id)
    _ensure_order_mutable(order, user)
    delete_stored_file(evidence.file_url)
    db.delete(evidence)
    db.commit()
