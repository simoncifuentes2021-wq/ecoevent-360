from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import InventoryItemType, UserRole
from app.schemas.inventory_schema import (
    InventoryItemCreate,
    InventoryItemListResponse,
    InventoryItemRead,
    InventoryItemUpdate,
)
from app.services import inventory_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/inventory/items", tags=["inventory"])


@router.post(
    "",
    response_model=InventoryItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.LOGISTICS_OPERATOR))
    ],
)
def create_inventory_item(
    payload: InventoryItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = inventory_service.create_inventory_item(db, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="INVENTORY_ITEM_CREATED",
        module="inventory",
        entity_type="InventoryItem",
        entity_id=item.id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.get("", response_model=InventoryItemListResponse)
def list_inventory_items(
    q: str | None = None,
    item_type: InventoryItemType | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = inventory_service.list_inventory_items(
        db,
        user=current_user,
        q=q,
        item_type=item_type,
        is_active=is_active,
        page=page,
        limit=limit,
    )
    return InventoryItemListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/{item_id}", response_model=InventoryItemRead)
def get_inventory_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return inventory_service.ensure_can_access_item(db, current_user, item_id)


@router.patch(
    "/{item_id}",
    response_model=InventoryItemRead,
    dependencies=[
        Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.LOGISTICS_OPERATOR))
    ],
)
def update_inventory_item(
    item_id: UUID,
    payload: InventoryItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = inventory_service.get_inventory_item_or_404(db, item_id)
    old_data = serialize_model_for_audit(before)
    item = inventory_service.update_inventory_item(db, item_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="INVENTORY_ITEM_UPDATED",
        module="inventory",
        entity_type="InventoryItem",
        entity_id=item.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.delete(
    "/{item_id}",
    response_model=InventoryItemRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def delete_inventory_item(
    item_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = inventory_service.get_inventory_item_or_404(db, item_id)
    old_data = serialize_model_for_audit(before)
    item = inventory_service.deactivate_inventory_item(db, item_id)
    create_audit_log(
        db,
        user=current_user,
        action="INVENTORY_ITEM_DEACTIVATED",
        module="inventory",
        entity_type="InventoryItem",
        entity_id=item.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item
