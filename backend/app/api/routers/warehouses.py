from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User, WarehouseUser
from app.models.enums import UserRole
from app.schemas.warehouse_schema import (
    WarehouseCreate,
    WarehouseListResponse,
    WarehouseRead,
    WarehouseUpdate,
    WarehouseUserCreate,
    WarehouseUserRead,
    MyWarehouseAssignmentRead,
    WarehouseUserUpdate,
)
from app.services import warehouse_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.post(
    "",
    response_model=WarehouseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_warehouse(
    payload: WarehouseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    warehouse = warehouse_service.create_warehouse(db, payload)
    create_audit_log(
        db,
        user=current_user,
        action="WAREHOUSE_CREATED",
        module="warehouses",
        entity_type="Warehouse",
        entity_id=warehouse.id,
        new_data=serialize_model_for_audit(warehouse),
        request=request,
    )
    return warehouse


@router.get(
    "",
    response_model=WarehouseListResponse,
)
def list_warehouses(
    q: str | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = warehouse_service.list_warehouses(
        db, user=current_user, q=q, is_active=is_active, page=page, limit=limit
    )
    return WarehouseListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/me/assignments", response_model=list[MyWarehouseAssignmentRead])
def list_my_warehouse_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    assignments = warehouse_service.list_my_warehouse_assignments(db, current_user)
    return [
        MyWarehouseAssignmentRead(
            id=assignment.id,
            warehouse_id=assignment.warehouse_id,
            warehouse_name=assignment.warehouse.name,
            can_view_stock=assignment.can_view_stock,
            can_manage_stock=assignment.can_manage_stock,
            can_dispatch_orders=assignment.can_dispatch_orders,
            created_at=assignment.created_at,
        )
        for assignment in assignments
    ]


@router.get("/{warehouse_id}", response_model=WarehouseRead)
def get_warehouse(
    warehouse_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return warehouse_service.ensure_can_access_warehouse(db, current_user, warehouse_id)


@router.patch(
    "/{warehouse_id}",
    response_model=WarehouseRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_warehouse(
    warehouse_id: UUID,
    payload: WarehouseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = warehouse_service.get_warehouse_or_404(db, warehouse_id)
    old_data = serialize_model_for_audit(before)
    warehouse = warehouse_service.update_warehouse(db, warehouse_id, payload)
    create_audit_log(
        db,
        user=current_user,
        action="WAREHOUSE_UPDATED",
        module="warehouses",
        entity_type="Warehouse",
        entity_id=warehouse.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(warehouse),
        request=request,
    )
    return warehouse


@router.delete(
    "/{warehouse_id}",
    response_model=WarehouseRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def delete_warehouse(
    warehouse_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = warehouse_service.get_warehouse_or_404(db, warehouse_id)
    old_data = serialize_model_for_audit(before)
    warehouse = warehouse_service.deactivate_warehouse(db, warehouse_id)
    create_audit_log(
        db,
        user=current_user,
        action="WAREHOUSE_DEACTIVATED",
        module="warehouses",
        entity_type="Warehouse",
        entity_id=warehouse.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(warehouse),
        request=request,
    )
    return warehouse


@router.post(
    "/{warehouse_id}/users",
    response_model=WarehouseUserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def assign_warehouse_user(
    warehouse_id: UUID,
    payload: WarehouseUserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    assignment = warehouse_service.assign_warehouse_user(db, warehouse_id, payload)
    create_audit_log(
        db,
        user=current_user,
        action="WAREHOUSE_USER_ASSIGNED",
        module="warehouses",
        entity_type="WarehouseUser",
        entity_id=assignment.id,
        new_data=serialize_model_for_audit(assignment),
        request=request,
    )
    return _warehouse_user_read(assignment)


@router.get(
    "/{warehouse_id}/users",
    response_model=list[WarehouseUserRead],
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def list_warehouse_users(warehouse_id: UUID, db: Session = Depends(get_db)):
    assignments = warehouse_service.list_warehouse_users(db, warehouse_id)
    return [_warehouse_user_read(assignment) for assignment in assignments]


@router.patch(
    "/{warehouse_id}/users/{user_id}",
    response_model=WarehouseUserRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_warehouse_user(
    warehouse_id: UUID,
    user_id: UUID,
    payload: WarehouseUserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    assignment = warehouse_service.update_warehouse_user(db, warehouse_id, user_id, payload)
    create_audit_log(
        db,
        user=current_user,
        action="WAREHOUSE_USER_PERMISSIONS_UPDATED",
        module="warehouses",
        entity_type="WarehouseUser",
        entity_id=assignment.id,
        new_data=serialize_model_for_audit(assignment),
        request=request,
    )
    return _warehouse_user_read(assignment)


@router.delete(
    "/{warehouse_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def remove_warehouse_user(
    warehouse_id: UUID,
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    warehouse_service.remove_warehouse_user(db, warehouse_id, user_id)
    create_audit_log(
        db,
        user=current_user,
        action="WAREHOUSE_USER_REMOVED",
        module="warehouses",
        entity_type="WarehouseUser",
        entity_id=user_id,
        request=request,
    )


def _warehouse_user_read(assignment: WarehouseUser) -> WarehouseUserRead:
    user = getattr(assignment, "user", None)
    return WarehouseUserRead(
        id=assignment.id,
        warehouse_id=assignment.warehouse_id,
        user_id=assignment.user_id,
        can_view_stock=assignment.can_view_stock,
        can_manage_stock=assignment.can_manage_stock,
        can_dispatch_orders=assignment.can_dispatch_orders,
        created_at=assignment.created_at,
        user_full_name=user.full_name if user else None,
        user_email=user.email if user else None,
        user_role=user.role if user else None,
    )
