from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.purchase_order_schema import (
    PurchaseOrderCancel,
    PurchaseOrderCreate,
    PurchaseOrderListRead,
    PurchaseOrderRead,
    PurchaseOrderReceive,
)
from app.services import purchase_order_service as service
from app.services.audit_log_service import create_audit_log

router = APIRouter(tags=["independent purchase orders"])


@router.get("/purchase-orders", response_model=PurchaseOrderListRead)
def list_purchase_orders(
    status_filter: str | None = Query(default=None, alias="status"),
    event_id: UUID | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    rows, total = service.list_orders(db, user, status_filter=status_filter, event_id=event_id, q=q, page=page, limit=limit)
    return {"items": rows, "total": total, "page": page, "limit": limit}


@router.post("/purchase-orders", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_purchase_order(payload: PurchaseOrderCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    order = service.create_order(db, payload, user)
    create_audit_log(db, user=user, action="CREATE", module="purchase_orders", entity_type="PurchaseOrder", entity_id=order["id"], event_id=order["event_id"], new_data={"order_number": order["order_number"], "total": str(order["total"])}, request=request)
    return order


@router.get("/purchase-orders/{order_id}", response_model=PurchaseOrderRead)
def get_purchase_order(order_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.get_order(db, order_id, user)


@router.put("/purchase-orders/{order_id}", response_model=PurchaseOrderRead)
def update_purchase_order(order_id: UUID, payload: PurchaseOrderCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    before = service.get_order(db, order_id, user)
    order = service.update_order(db, order_id, payload, user)
    create_audit_log(db, user=user, action="UPDATE", module="purchase_orders", entity_type="PurchaseOrder", entity_id=order["id"], event_id=order["event_id"], old_data={"version": before["version"], "total": str(before["total"])}, new_data={"version": order["version"], "total": str(order["total"])}, request=request)
    return order


@router.post("/purchase-orders/{order_id}/approve", response_model=PurchaseOrderRead)
def approve_purchase_order(order_id: UUID, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    order = service.change_status(db, order_id, "approve", user)
    create_audit_log(db, user=user, action="APPROVE", module="purchase_orders", entity_type="PurchaseOrder", entity_id=order["id"], event_id=order["event_id"], new_data={"status": order["status"]}, request=request)
    return order


@router.post("/purchase-orders/{order_id}/send", response_model=PurchaseOrderRead)
def send_purchase_order(order_id: UUID, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    order = service.change_status(db, order_id, "send", user)
    create_audit_log(db, user=user, action="MARK_SENT", module="purchase_orders", entity_type="PurchaseOrder", entity_id=order["id"], event_id=order["event_id"], new_data={"status": order["status"], "supplier_email": order["supplier_email"]}, request=request)
    return order


@router.post("/purchase-orders/{order_id}/receive", response_model=PurchaseOrderRead)
def receive_purchase_order(order_id: UUID, payload: PurchaseOrderReceive, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    order = service.receive_order(db, order_id, payload, user)
    create_audit_log(db, user=user, action="RECEIVE", module="purchase_orders", entity_type="PurchaseOrder", entity_id=order["id"], event_id=order["event_id"], new_data={"status": order["status"], "items": [item.model_dump(mode="json") for item in payload.items]}, request=request)
    return order


@router.post("/purchase-orders/{order_id}/cancel", response_model=PurchaseOrderRead)
def cancel_purchase_order(order_id: UUID, payload: PurchaseOrderCancel, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    order = service.cancel_order(db, order_id, payload.reason, user)
    create_audit_log(db, user=user, action="CANCEL", module="purchase_orders", entity_type="PurchaseOrder", entity_id=order["id"], event_id=order["event_id"], new_data={"status": order["status"], "reason": payload.reason}, request=request)
    return order


@router.get("/purchase-orders/{order_id}/pdf")
def purchase_order_pdf(order_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    content, number = service.render_pdf(db, order_id, user)
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{number}.pdf"', "Cache-Control": "private, no-store"})
