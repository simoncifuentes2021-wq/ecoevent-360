from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.models.enums import PurchaseDeliveryMode, PurchaseRequestStatus
from app.schemas.purchase_request_schema import (
    PurchaseRequestCreate,
    PurchaseRequestFromOrderCreate,
    PurchaseRequestListResponse,
    PurchaseRequestMarkPurchased,
    PurchaseRequestRead,
    PurchaseRequestReceive,
    PurchaseRequestReject,
    PurchaseRequestUpdate,
)
from app.services import purchase_request_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(tags=["purchase requests"])


@router.post(
    "/purchase-requests",
    response_model=PurchaseRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_purchase_request(
    payload: PurchaseRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    purchase = purchase_request_service.create_purchase_request(db, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="PURCHASE_REQUEST_CREATED",
        module="purchase_requests",
        entity_type="PurchaseRequest",
        entity_id=purchase.id,
        event_id=purchase.event_id,
        new_data=serialize_model_for_audit(purchase),
        request=request,
    )
    return purchase


@router.get("/purchase-requests", response_model=PurchaseRequestListResponse)
def list_purchase_requests(
    status_filter: PurchaseRequestStatus | None = Query(default=None, alias="status"),
    delivery_mode: PurchaseDeliveryMode | None = None,
    event_id: UUID | None = None,
    logistics_order_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = purchase_request_service.list_purchase_requests(
        db,
        user=current_user,
        status_filter=status_filter,
        delivery_mode=delivery_mode,
        event_id=event_id,
        logistics_order_id=logistics_order_id,
        warehouse_id=warehouse_id,
        q=q,
        page=page,
        limit=limit,
    )
    return PurchaseRequestListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/purchase-requests/{purchase_request_id}", response_model=PurchaseRequestRead)
def get_purchase_request(
    purchase_request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return purchase_request_service.get_purchase_request_detail(db, purchase_request_id, current_user)


@router.patch("/purchase-requests/{purchase_request_id}", response_model=PurchaseRequestRead)
def update_purchase_request(
    purchase_request_id: UUID,
    payload: PurchaseRequestUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    purchase = purchase_request_service.update_purchase_request(db, purchase_request_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="PURCHASE_REQUEST_UPDATED",
        module="purchase_requests",
        entity_type="PurchaseRequest",
        entity_id=purchase.id,
        event_id=purchase.event_id,
        new_data=serialize_model_for_audit(purchase),
        request=request,
    )
    return purchase


@router.post("/purchase-requests/{purchase_request_id}/approve", response_model=PurchaseRequestRead)
def approve_purchase_request(
    purchase_request_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    purchase = purchase_request_service.approve_purchase_request(db, purchase_request_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="PURCHASE_REQUEST_APPROVED",
        module="purchase_requests",
        entity_type="PurchaseRequest",
        entity_id=purchase.id,
        event_id=purchase.event_id,
        request=request,
    )
    return purchase


@router.post("/purchase-requests/{purchase_request_id}/reject", response_model=PurchaseRequestRead)
def reject_purchase_request(
    purchase_request_id: UUID,
    payload: PurchaseRequestReject,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    purchase = purchase_request_service.reject_purchase_request(db, purchase_request_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="PURCHASE_REQUEST_REJECTED",
        module="purchase_requests",
        entity_type="PurchaseRequest",
        entity_id=purchase.id,
        event_id=purchase.event_id,
        request=request,
    )
    return purchase


@router.post("/purchase-requests/{purchase_request_id}/mark-purchased", response_model=PurchaseRequestRead)
def mark_purchase_request_purchased(
    purchase_request_id: UUID,
    payload: PurchaseRequestMarkPurchased,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    purchase = purchase_request_service.mark_purchase_request_purchased(db, purchase_request_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="PURCHASE_REQUEST_MARKED_PURCHASED",
        module="purchase_requests",
        entity_type="PurchaseRequest",
        entity_id=purchase.id,
        event_id=purchase.event_id,
        request=request,
    )
    return purchase


@router.post("/purchase-requests/{purchase_request_id}/receive", response_model=PurchaseRequestRead)
def receive_purchase_request(
    purchase_request_id: UUID,
    payload: PurchaseRequestReceive,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    purchase = purchase_request_service.receive_purchase_request(db, purchase_request_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="PURCHASE_REQUEST_RECEIVED",
        module="purchase_requests",
        entity_type="PurchaseRequest",
        entity_id=purchase.id,
        event_id=purchase.event_id,
        request=request,
    )
    return purchase


@router.post("/purchase-requests/{purchase_request_id}/deliver-direct-to-event", response_model=PurchaseRequestRead)
def deliver_purchase_request_direct_to_event(
    purchase_request_id: UUID,
    payload: PurchaseRequestReceive,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    purchase = purchase_request_service.deliver_direct_to_event(db, purchase_request_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="PURCHASE_REQUEST_DELIVERED_DIRECT_TO_EVENT",
        module="purchase_requests",
        entity_type="PurchaseRequest",
        entity_id=purchase.id,
        event_id=purchase.event_id,
        request=request,
    )
    return purchase


@router.post("/purchase-requests/{purchase_request_id}/cancel", response_model=PurchaseRequestRead)
def cancel_purchase_request(
    purchase_request_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    purchase = purchase_request_service.cancel_purchase_request(db, purchase_request_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="PURCHASE_REQUEST_CANCELLED",
        module="purchase_requests",
        entity_type="PurchaseRequest",
        entity_id=purchase.id,
        event_id=purchase.event_id,
        request=request,
    )
    return purchase


@router.post(
    "/logistics-orders/{order_id}/purchase-request",
    response_model=PurchaseRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_purchase_request_from_order(
    order_id: UUID,
    payload: PurchaseRequestFromOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    purchase = purchase_request_service.create_purchase_request_from_order(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="PURCHASE_REQUEST_CREATED_FROM_LOGISTICS_ORDER",
        module="purchase_requests",
        entity_type="PurchaseRequest",
        entity_id=purchase.id,
        event_id=purchase.event_id,
        request=request,
    )
    return purchase


@router.get("/logistics-orders/{order_id}/purchase-requests", response_model=PurchaseRequestListResponse)
def list_purchase_requests_for_order(
    order_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = purchase_request_service.list_purchase_requests(
        db,
        user=current_user,
        status_filter=None,
        delivery_mode=None,
        event_id=None,
        logistics_order_id=order_id,
        warehouse_id=None,
        q=None,
        page=page,
        limit=limit,
    )
    return PurchaseRequestListResponse(items=items, total=total, page=page, limit=limit)
