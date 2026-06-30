from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import LogisticsOrderStatus, UserRole
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
    LogisticsOrderItemRead,
    LogisticsOrderItemUpdate,
    LogisticsOrderListResponse,
    LogisticsOrderOutcomeConfirm,
    LogisticsOrderRead,
    LogisticsOrderStockCheckResponse,
    LogisticsOrderUpdate,
)
from app.services import logistics_order_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(tags=["logistics orders"])


@router.post(
    "/events/{event_id}/logistics-orders",
    response_model=LogisticsOrderRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR))],
)
def create_event_logistics_order(
    event_id: UUID,
    payload: LogisticsOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = logistics_order_service.create_logistics_order(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_CREATED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.get("/events/{event_id}/logistics-orders", response_model=LogisticsOrderListResponse)
def list_event_logistics_orders(
    event_id: UUID,
    status_filter: LogisticsOrderStatus | None = Query(default=None, alias="status"),
    assigned_operator_id: UUID | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = logistics_order_service.list_logistics_orders(
        db,
        user=current_user,
        event_id=event_id,
        status_filter=status_filter,
        assigned_operator_id=assigned_operator_id,
        q=q,
        page=page,
        limit=limit,
    )
    return LogisticsOrderListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/logistics-orders", response_model=LogisticsOrderListResponse)
def list_logistics_orders(
    event_id: UUID | None = None,
    status_filter: LogisticsOrderStatus | None = Query(default=None, alias="status"),
    assigned_operator_id: UUID | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = logistics_order_service.list_logistics_orders(
        db,
        user=current_user,
        event_id=event_id,
        status_filter=status_filter,
        assigned_operator_id=assigned_operator_id,
        q=q,
        page=page,
        limit=limit,
    )
    return LogisticsOrderListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/me/logistics-orders", response_model=LogisticsOrderListResponse)
def list_my_logistics_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = logistics_order_service.list_logistics_orders(
        db,
        user=current_user,
        event_id=None,
        status_filter=None,
        assigned_operator_id=current_user.id,
        q=None,
        page=page,
        limit=limit,
    )
    return LogisticsOrderListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/logistics-orders/{order_id}", response_model=LogisticsOrderRead)
def get_logistics_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return logistics_order_service.get_logistics_order_detail(db, order_id, current_user)


@router.get("/logistics-orders/{order_id}/stock-check", response_model=LogisticsOrderStockCheckResponse)
def check_logistics_order_stock(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return logistics_order_service.check_logistics_order_stock(db, order_id, current_user)


@router.post("/logistics-orders/{order_id}/reserve", response_model=LogisticsOrderRead)
def reserve_logistics_order_stock(
    order_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = logistics_order_service.reserve_logistics_order_stock(db, order_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_STOCK_RESERVED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.post("/logistics-orders/{order_id}/unreserve", response_model=LogisticsOrderRead)
def unreserve_logistics_order_stock(
    order_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = logistics_order_service.unreserve_logistics_order_stock(db, order_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_STOCK_UNRESERVED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.post("/logistics-orders/{order_id}/start-preparation", response_model=LogisticsOrderRead)
def start_logistics_order_preparation(
    order_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = logistics_order_service.start_logistics_order_preparation(db, order_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_PREPARATION_STARTED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.patch("/logistics-order-items/{item_id}/load", response_model=LogisticsOrderItemRead)
def load_logistics_order_item(
    item_id: UUID,
    payload: LogisticsOrderItemLoad,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = logistics_order_service.load_logistics_order_item(db, item_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_ITEM_LOADED",
        module="logistics_orders",
        entity_type="LogisticsOrderItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.post("/logistics-orders/{order_id}/dispatch", response_model=LogisticsOrderRead)
def dispatch_logistics_order(
    order_id: UUID,
    payload: LogisticsOrderDispatch,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = logistics_order_service.dispatch_logistics_order(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_DISPATCHED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.patch("/logistics-order-items/{item_id}/deliver", response_model=LogisticsOrderItemRead)
def deliver_logistics_order_item(
    item_id: UUID,
    payload: LogisticsOrderItemDeliver,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = logistics_order_service.deliver_logistics_order_item(db, item_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_ITEM_DELIVERED",
        module="logistics_orders",
        entity_type="LogisticsOrderItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.post("/logistics-orders/{order_id}/confirm-delivery", response_model=LogisticsOrderRead)
def confirm_logistics_order_delivery(
    order_id: UUID,
    payload: LogisticsOrderDeliveryConfirm,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = logistics_order_service.confirm_logistics_order_delivery(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_DELIVERY_CONFIRMED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.patch("/logistics-order-items/{item_id}/outcome", response_model=LogisticsOrderItemRead)
def register_logistics_order_item_outcome(
    item_id: UUID,
    payload: LogisticsOrderItemOutcome,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = logistics_order_service.register_logistics_order_item_outcome(db, item_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_ITEM_OUTCOME_RECORDED",
        module="logistics_orders",
        entity_type="LogisticsOrderItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.post("/logistics-orders/{order_id}/confirm-outcome", response_model=LogisticsOrderRead)
def confirm_logistics_order_outcome(
    order_id: UUID,
    payload: LogisticsOrderOutcomeConfirm,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = logistics_order_service.confirm_logistics_order_outcome(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_OUTCOME_CONFIRMED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.post("/logistics-orders/{order_id}/close", response_model=LogisticsOrderRead)
def close_logistics_order(
    order_id: UUID,
    payload: LogisticsOrderClose,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = logistics_order_service.close_logistics_order(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_CLOSED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data={
            "order_id": str(order.id),
            "closed_by": str(order.closed_by) if order.closed_by else None,
            "closed_at": order.closed_at.isoformat() if order.closed_at else None,
        },
        request=request,
    )
    return order


@router.patch("/logistics-orders/{order_id}", response_model=LogisticsOrderRead)
def update_logistics_order(
    order_id: UUID,
    payload: LogisticsOrderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = logistics_order_service.get_logistics_order_or_404(db, order_id)
    old_data = serialize_model_for_audit(before)
    order = logistics_order_service.update_logistics_order(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_UPDATED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.patch("/logistics-orders/{order_id}/assign", response_model=LogisticsOrderRead)
def assign_logistics_order(
    order_id: UUID,
    payload: LogisticsOrderAssign,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = logistics_order_service.assign_logistics_order(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_ASSIGNED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data={"assigned_operator_id": str(order.assigned_operator_id)},
        request=request,
    )
    return order


@router.patch("/logistics-orders/{order_id}/cancel", response_model=LogisticsOrderRead)
def cancel_logistics_order(
    order_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = logistics_order_service.cancel_logistics_order(db, order_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_CANCELLED",
        module="logistics_orders",
        entity_type="LogisticsOrder",
        entity_id=order.id,
        event_id=order.event_id,
        request=request,
    )
    return order


@router.post(
    "/logistics-orders/{order_id}/items",
    response_model=LogisticsOrderItemRead,
    status_code=status.HTTP_201_CREATED,
)
def add_logistics_order_item(
    order_id: UUID,
    payload: LogisticsOrderItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = logistics_order_service.add_logistics_order_item(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_ITEM_CREATED",
        module="logistics_orders",
        entity_type="LogisticsOrderItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.patch("/logistics-order-items/{item_id}", response_model=LogisticsOrderItemRead)
def update_logistics_order_item(
    item_id: UUID,
    payload: LogisticsOrderItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = logistics_order_service.get_logistics_order_item_or_404(db, item_id)
    old_data = serialize_model_for_audit(before)
    item = logistics_order_service.update_logistics_order_item(db, item_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_ITEM_UPDATED",
        module="logistics_orders",
        entity_type="LogisticsOrderItem",
        entity_id=item.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.delete("/logistics-order-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_logistics_order_item(
    item_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    logistics_order_service.delete_logistics_order_item(db, item_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="LOGISTICS_ORDER_ITEM_DELETED",
        module="logistics_orders",
        entity_type="LogisticsOrderItem",
        entity_id=item_id,
        request=request,
    )
