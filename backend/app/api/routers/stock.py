from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import StockMovementType, UserRole
from app.schemas.stock_schema import (
    StockBalanceCreate,
    StockBalanceListResponse,
    StockBalanceRead,
    StockBalanceUpdate,
    StockMovementCreate,
    StockMovementListResponse,
    StockMovementRead,
)
from app.services import stock_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/stock", tags=["stock"])
warehouse_stock_router = APIRouter(prefix="/warehouses", tags=["stock"])
inventory_stock_router = APIRouter(prefix="/inventory/items", tags=["stock"])


@router.get("", response_model=StockBalanceListResponse)
def list_stock_balances(
    warehouse_id: UUID | None = None,
    item_id: UUID | None = None,
    q: str | None = None,
    low_stock: bool | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = stock_service.list_stock_balances(
        db,
        user=current_user,
        warehouse_id=warehouse_id,
        item_id=item_id,
        q=q,
        low_stock=low_stock,
        page=page,
        limit=limit,
    )
    return StockBalanceListResponse(
        items=[stock_service.stock_balance_to_read(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.post(
    "/movements",
    response_model=StockMovementRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.LOGISTICS_OPERATOR))
    ],
)
def create_stock_movement(
    payload: StockMovementCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    movement = stock_service.create_stock_movement(db, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="STOCK_MOVEMENT_CREATED",
        module="stock",
        entity_type="StockMovement",
        entity_id=movement.id,
        new_data=serialize_model_for_audit(movement),
        request=request,
    )
    return stock_service.stock_movement_to_read(movement)


@router.get("/movements", response_model=StockMovementListResponse)
def list_stock_movements(
    warehouse_id: UUID | None = None,
    item_id: UUID | None = None,
    movement_type: StockMovementType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = stock_service.list_stock_movements(
        db,
        user=current_user,
        warehouse_id=warehouse_id,
        item_id=item_id,
        stock_balance_id=None,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        q=q,
        page=page,
        limit=limit,
    )
    return StockMovementListResponse(
        items=[stock_service.stock_movement_to_read(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/movements/{movement_id}", response_model=StockMovementRead)
def get_stock_movement(
    movement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    movement = stock_service.ensure_can_access_stock_movement(db, current_user, movement_id)
    return stock_service.stock_movement_to_read(movement)


@router.get("/{stock_id}", response_model=StockBalanceRead)
def get_stock_balance(
    stock_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stock = stock_service.ensure_can_access_stock_balance(db, current_user, stock_id)
    return stock_service.stock_balance_to_read(stock)


@router.get("/{stock_id}/movements", response_model=StockMovementListResponse)
def list_stock_balance_movements(
    stock_id: UUID,
    movement_type: StockMovementType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stock = stock_service.ensure_can_access_stock_balance(db, current_user, stock_id)
    items, total = stock_service.list_stock_movements(
        db,
        user=current_user,
        warehouse_id=None,
        item_id=None,
        stock_balance_id=stock.id,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        q=None,
        page=page,
        limit=limit,
    )
    return StockMovementListResponse(
        items=[stock_service.stock_movement_to_read(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.post(
    "",
    response_model=StockBalanceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))
    ],
)
def create_stock_balance(
    payload: StockBalanceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stock = stock_service.create_stock_balance(db, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="STOCK_BALANCE_CREATED_OR_UPDATED",
        module="stock",
        entity_type="StockBalance",
        entity_id=stock.id,
        new_data=serialize_model_for_audit(stock),
        request=request,
    )
    return stock_service.stock_balance_to_read(stock)


@router.patch(
    "/{stock_id}",
    response_model=StockBalanceRead,
    dependencies=[
        Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))
    ],
)
def update_stock_balance(
    stock_id: UUID,
    payload: StockBalanceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = stock_service.get_stock_balance_or_404(db, stock_id)
    old_data = serialize_model_for_audit(before)
    stock = stock_service.update_stock_balance(db, stock_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="STOCK_BALANCE_UPDATED",
        module="stock",
        entity_type="StockBalance",
        entity_id=stock.id,
        old_data=old_data,
        new_data=serialize_model_for_audit(stock),
        request=request,
    )
    return stock_service.stock_balance_to_read(stock)


@warehouse_stock_router.get(
    "/{warehouse_id}/stock",
    response_model=StockBalanceListResponse,
)
def list_warehouse_stock(
    warehouse_id: UUID,
    q: str | None = None,
    low_stock: bool | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = stock_service.list_stock_balances(
        db,
        user=current_user,
        warehouse_id=warehouse_id,
        item_id=None,
        q=q,
        low_stock=low_stock,
        page=page,
        limit=limit,
    )
    return StockBalanceListResponse(
        items=[stock_service.stock_balance_to_read(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )


@warehouse_stock_router.get(
    "/{warehouse_id}/movements",
    response_model=StockMovementListResponse,
)
def list_warehouse_stock_movements(
    warehouse_id: UUID,
    movement_type: StockMovementType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = stock_service.list_stock_movements(
        db,
        user=current_user,
        warehouse_id=warehouse_id,
        item_id=None,
        stock_balance_id=None,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        q=q,
        page=page,
        limit=limit,
    )
    return StockMovementListResponse(
        items=[stock_service.stock_movement_to_read(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )


@inventory_stock_router.get(
    "/{item_id}/stock",
    response_model=StockBalanceListResponse,
)
def list_inventory_item_stock(
    item_id: UUID,
    warehouse_id: UUID | None = None,
    low_stock: bool | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = stock_service.list_stock_balances(
        db,
        user=current_user,
        warehouse_id=warehouse_id,
        item_id=item_id,
        q=None,
        low_stock=low_stock,
        page=page,
        limit=limit,
    )
    return StockBalanceListResponse(
        items=[stock_service.stock_balance_to_read(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )


@inventory_stock_router.get(
    "/{item_id}/movements",
    response_model=StockMovementListResponse,
)
def list_inventory_item_stock_movements(
    item_id: UUID,
    warehouse_id: UUID | None = None,
    movement_type: StockMovementType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = stock_service.list_stock_movements(
        db,
        user=current_user,
        warehouse_id=warehouse_id,
        item_id=item_id,
        stock_balance_id=None,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        q=None,
        page=page,
        limit=limit,
    )
    return StockMovementListResponse(
        items=[stock_service.stock_movement_to_read(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )
