from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import OrderEvidenceStage, OrderStatus, UserRole
from app.schemas.order_schema import (
    CatalogItemCreate,
    CatalogItemListResponse,
    CatalogItemRead,
    CatalogItemUpdate,
    EventOrderCreate,
    EventOrderDetailRead,
    EventOrderItemCreate,
    EventOrderItemRead,
    EventOrderItemUpdate,
    EventOrderListResponse,
    EventOrderRead,
    EventOrderStatusUpdate,
    EventOrderUpdate,
    OrderEvidenceCreate,
    OrderEvidenceRead,
    OrderItemStageUpdate,
)
from app.services import order_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(tags=["orders"])


@router.get("/catalog-items", response_model=CatalogItemListResponse)
def list_catalog_items(
    q: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role in {UserRole.CLIENT, UserRole.WORKER}:
        return CatalogItemListResponse(items=[], total=0, page=page, limit=limit)
    items, total = order_service.list_catalog_items(
        db, q=q, category=category, is_active=is_active, page=page, limit=limit
    )
    return CatalogItemListResponse(items=items, total=total, page=page, limit=limit)


@router.post(
    "/catalog-items",
    response_model=CatalogItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_catalog_item(
    payload: CatalogItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = order_service.create_catalog_item(db, payload)
    create_audit_log(
        db,
        user=current_user,
        action="CATALOG_ITEM_CREATED",
        module="orders",
        entity_type="CatalogItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.get("/catalog-items/{item_id}", response_model=CatalogItemRead)
def get_catalog_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role in {UserRole.CLIENT, UserRole.WORKER}:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return order_service.get_catalog_item_or_404(db, item_id)


@router.patch(
    "/catalog-items/{item_id}",
    response_model=CatalogItemRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_catalog_item(
    item_id: UUID,
    payload: CatalogItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = order_service.get_catalog_item_or_404(db, item_id)
    old_data = serialize_model_for_audit(before)
    item = order_service.update_catalog_item(db, item_id, payload)
    create_audit_log(
        db,
        user=current_user,
        action="CATALOG_ITEM_UPDATED",
        module="orders",
        entity_type="CatalogItem",
        entity_id=item.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.delete(
    "/catalog-items/{item_id}",
    response_model=CatalogItemRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def deactivate_catalog_item(
    item_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = order_service.deactivate_catalog_item(db, item_id)
    create_audit_log(
        db,
        user=current_user,
        action="CATALOG_ITEM_DEACTIVATED",
        module="orders",
        entity_type="CatalogItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.post(
    "/events/{event_id}/orders",
    response_model=EventOrderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_event_order(
    event_id: UUID,
    payload: EventOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = order_service.create_order(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_CREATED",
        module="orders",
        entity_type="EventOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.get("/events/{event_id}/orders", response_model=EventOrderListResponse)
def list_event_orders(
    event_id: UUID,
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    assigned_to: UUID | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = order_service.list_event_orders(
        db,
        event_id=event_id,
        user=current_user,
        status_filter=status_filter,
        assigned_to=assigned_to,
        page=page,
        limit=limit,
    )
    return EventOrderListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/me/orders", response_model=EventOrderListResponse)
def list_my_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = order_service.list_my_orders(db, user=current_user, page=page, limit=limit)
    return EventOrderListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/orders/{order_id}", response_model=EventOrderDetailRead)
def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return order_service.get_order_detail(db, order_id, current_user)


@router.patch("/orders/{order_id}", response_model=EventOrderRead)
def update_order(
    order_id: UUID,
    payload: EventOrderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = order_service.get_order_or_404(db, order_id)
    old_data = serialize_model_for_audit(before)
    order = order_service.update_order(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_UPDATED",
        module="orders",
        entity_type="EventOrder",
        entity_id=order.id,
        event_id=order.event_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.patch("/orders/{order_id}/status", response_model=EventOrderRead)
def update_order_status(
    order_id: UUID,
    payload: EventOrderStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = order_service.update_order_status(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_STATUS_CHANGED",
        module="orders",
        entity_type="EventOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data={"status": order.status},
        request=request,
    )
    return order


@router.delete("/orders/{order_id}", response_model=EventOrderRead)
def cancel_order(
    order_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = order_service.cancel_order(db, order_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_CANCELLED",
        module="orders",
        entity_type="EventOrder",
        entity_id=order.id,
        event_id=order.event_id,
        new_data=serialize_model_for_audit(order),
        request=request,
    )
    return order


@router.post(
    "/orders/{order_id}/items",
    response_model=EventOrderItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_order_item(
    order_id: UUID,
    payload: EventOrderItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = order_service.create_order_item(db, order_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_ITEM_CREATED",
        module="orders",
        entity_type="EventOrderItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.patch("/orders/{order_id}/items/{item_id}", response_model=EventOrderItemRead)
def update_order_item(
    order_id: UUID,
    item_id: UUID,
    payload: EventOrderItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = order_service.update_order_item(db, order_id, item_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_ITEM_UPDATED",
        module="orders",
        entity_type="EventOrderItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.delete("/orders/{order_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_item(
    order_id: UUID,
    item_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order_service.delete_order_item(db, order_id, item_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_ITEM_DELETED",
        module="orders",
        entity_type="EventOrderItem",
        entity_id=item_id,
        request=request,
    )


@router.patch("/order-items/{item_id}/load", response_model=EventOrderItemRead)
def mark_item_loaded(
    item_id: UUID,
    payload: OrderItemStageUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = order_service.update_item_stage(
        db, item_id, payload, current_user, stage=OrderEvidenceStage.LOAD
    )
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_ITEM_LOADED",
        module="orders",
        entity_type="EventOrderItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.patch("/order-items/{item_id}/deliver", response_model=EventOrderItemRead)
def mark_item_delivered(
    item_id: UUID,
    payload: OrderItemStageUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = order_service.update_item_stage(
        db, item_id, payload, current_user, stage=OrderEvidenceStage.DELIVERY
    )
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_ITEM_DELIVERED",
        module="orders",
        entity_type="EventOrderItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.patch("/order-items/{item_id}/return", response_model=EventOrderItemRead)
def mark_item_returned(
    item_id: UUID,
    payload: OrderItemStageUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = order_service.update_item_stage(
        db, item_id, payload, current_user, stage=OrderEvidenceStage.RETURN
    )
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_ITEM_RETURNED",
        module="orders",
        entity_type="EventOrderItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.post(
    "/orders/{order_id}/evidences",
    response_model=OrderEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_order_evidence(
    order_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    stage: OrderEvidenceStage = Form(...),
    order_item_id: UUID | None = Form(default=None),
    description: str | None = Form(default=None),
    visible_to_client: bool = Form(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    evidence = order_service.create_order_evidence(
        db,
        order_id,
        OrderEvidenceCreate(
            stage=stage,
            order_item_id=order_item_id,
            description=description,
            visible_to_client=visible_to_client,
        ),
        file,
        current_user,
    )
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_EVIDENCE_UPLOADED",
        module="orders",
        entity_type="OrderEvidence",
        entity_id=evidence.id,
        event_id=evidence.event_id,
        new_data=serialize_model_for_audit(evidence),
        request=request,
    )
    return evidence


@router.get("/orders/{order_id}/evidences", response_model=list[OrderEvidenceRead])
def list_order_evidences(
    order_id: UUID,
    stage: OrderEvidenceStage | None = None,
    order_item_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return order_service.list_order_evidences(
        db, order_id=order_id, user=current_user, stage=stage, order_item_id=order_item_id
    )


@router.delete("/order-evidences/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_evidence(
    evidence_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order_service.delete_order_evidence(db, evidence_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ORDER_EVIDENCE_DELETED",
        module="orders",
        entity_type="OrderEvidence",
        entity_id=evidence_id,
        request=request,
    )
