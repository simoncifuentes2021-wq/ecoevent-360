"""Verify the logistics stock/purchase flow without persisting QA data."""

from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine, set_rls_context
from app.models.core import Event, InventoryItem, LogisticsOrder, StockBalance, StockMovement, User, Warehouse
from app.models.enums import (
    InventoryItemType,
    LogisticsOrderStatus,
    PurchaseDeliveryMode,
    PurchaseRequestStatus,
    StockMovementType,
    UserRole,
)
from app.schemas.logistics_order_schema import (
    LogisticsOrderCreate,
    LogisticsOrderItemCreate,
    LogisticsOrderStockTransferCreate,
    LogisticsPartialDispatchRequestCreate,
    LogisticsPartialDispatchReview,
)
from app.schemas.purchase_request_schema import (
    PurchaseRequestFromOrderCreate,
    PurchaseRequestMarkPurchased,
    PurchaseRequestMarkPurchasedItem,
    PurchaseRequestReceive,
    PurchaseRequestReceiveItem,
)
from app.services.logistics_order_service import (
    cancel_logistics_order,
    approve_partial_dispatch_request,
    create_partial_dispatch_request,
    create_logistics_order,
    get_logistics_order_stock_availability,
    reserve_logistics_order_stock,
    transfer_stock_to_logistics_order,
)
from app.services.purchase_request_service import (
    approve_purchase_request,
    create_purchase_request_from_order,
    mark_purchase_request_purchased,
    receive_purchase_request,
)


def _expect_http_error(expected_status: int, action) -> None:
    try:
        action()
    except HTTPException as exc:
        if exc.status_code != expected_status:
            raise AssertionError(f"Expected HTTP {expected_status}, received {exc.status_code}: {exc.detail}") from exc
        return
    raise AssertionError(f"Expected HTTP {expected_status}, but the operation succeeded")


def _assert_decimal(actual: Decimal, expected: str, label: str) -> None:
    expected_value = Decimal(expected)
    if actual != expected_value:
        raise AssertionError(f"{label}: expected {expected_value}, received {actual}")


def _find_fixture_data(db: Session) -> tuple[User, User, Event, Warehouse, Warehouse]:
    admin = db.scalar(
        select(User)
        .where(User.role.in_({UserRole.SUPER_ADMIN, UserRole.ADMIN}), User.is_active.is_(True))
        .order_by(User.created_at.asc())
    )
    operator = db.scalar(
        select(User)
        .where(User.role == UserRole.LOGISTICS_OPERATOR, User.is_active.is_(True))
        .order_by(User.created_at.asc())
    )
    event = db.scalar(select(Event).order_by(Event.created_at.desc()))
    warehouses = list(
        db.scalars(select(Warehouse).where(Warehouse.is_active.is_(True)).order_by(Warehouse.created_at.asc())).all()
    )
    if not admin or not operator or not event or len(warehouses) < 2:
        raise RuntimeError("The verification requires an admin, an operator, an event and two active warehouses")
    return admin, operator, event, warehouses[0], warehouses[1]


def _create_item_and_stock(
    db: Session,
    *,
    marker: str,
    suffix: str,
    warehouse: Warehouse,
    quantity: str,
) -> InventoryItem:
    item = InventoryItem(
        sku=f"QA-{marker}-{suffix}",
        name=f"QA flujo logistico {marker} {suffix}",
        item_type=InventoryItemType.CONSUMABLE,
        return_required=False,
        unit="unidad",
        unit_price=Decimal("1000"),
        replacement_cost=Decimal("1000"),
        min_stock=Decimal("0"),
        is_active=True,
    )
    db.add(item)
    db.flush()
    db.add(
        StockBalance(
            warehouse_id=warehouse.id,
            item_id=item.id,
            quantity_on_hand=Decimal(quantity),
            quantity_reserved=Decimal("0"),
            quantity_damaged=Decimal("0"),
        )
    )
    db.flush()
    return item


def _create_order(
    db: Session,
    *,
    marker: str,
    suffix: str,
    event: Event,
    warehouse: Warehouse,
    operator: User,
    admin: User,
    item: InventoryItem,
    quantity: str,
) -> LogisticsOrder:
    return create_logistics_order(
        db,
        event.id,
        LogisticsOrderCreate(
            warehouse_id=warehouse.id,
            assigned_operator_id=operator.id,
            title=f"QA pedido logistico {marker} {suffix}",
            items=[LogisticsOrderItemCreate(item_id=item.id, quantity_requested=Decimal(quantity))],
        ),
        admin,
    )


def run_verification() -> list[str]:
    marker = uuid4().hex[:10]
    connection = engine.connect()
    outer_transaction = connection.begin()
    db = Session(bind=connection, expire_on_commit=False, join_transaction_mode="rollback_only")
    results: list[str] = []

    try:
        admin, operator, event, warehouse, other_warehouse = _find_fixture_data(db)
        set_rls_context(db, user_id=admin.id, role=admin.role, client_id=admin.client_id)

        full_item = _create_item_and_stock(
            db,
            marker=marker,
            suffix="completo",
            warehouse=warehouse,
            quantity="10",
        )
        full_order = _create_order(
            db,
            marker=marker,
            suffix="completo",
            event=event,
            warehouse=warehouse,
            operator=operator,
            admin=admin,
            item=full_item,
            quantity="5",
        )
        full_order = reserve_logistics_order_stock(db, full_order.id, admin)
        if full_order.status != LogisticsOrderStatus.RESERVED:
            raise AssertionError(f"Full-stock order ended in {full_order.status}")
        _assert_decimal(full_order.items[0].quantity_reserved, "5", "Full reservation")
        full_order = cancel_logistics_order(db, full_order.id, admin)
        full_stock = db.scalar(
            select(StockBalance).where(
                StockBalance.warehouse_id == warehouse.id,
                StockBalance.item_id == full_item.id,
            )
        )
        if full_order.status != LogisticsOrderStatus.CANCELLED or not full_stock:
            raise AssertionError("The full-stock order was not cancelled correctly")
        _assert_decimal(full_stock.quantity_reserved, "0", "Released full reservation")
        results.append("Stock completo: reserva total y cancelacion liberan correctamente")

        partial_item = _create_item_and_stock(
            db,
            marker=marker,
            suffix="parcial",
            warehouse=warehouse,
            quantity="3",
        )
        partial_order = _create_order(
            db,
            marker=marker,
            suffix="parcial",
            event=event,
            warehouse=warehouse,
            operator=operator,
            admin=admin,
            item=partial_item,
            quantity="8",
        )
        partial_order = reserve_logistics_order_stock(db, partial_order.id, admin)
        if partial_order.status != LogisticsOrderStatus.INSUFFICIENT_STOCK:
            raise AssertionError(f"Partial-stock order ended in {partial_order.status}")
        _assert_decimal(partial_order.items[0].quantity_reserved, "3", "Partial reservation")
        _assert_decimal(partial_order.items[0].quantity_missing, "5", "Partial missing quantity")
        results.append("Stock parcial: reserva 3 y calcula faltante 5 correctamente")

        _expect_http_error(
            400,
            lambda: create_purchase_request_from_order(
                db,
                partial_order.id,
                PurchaseRequestFromOrderCreate(
                    title="QA entrega directa bloqueada",
                    delivery_mode=PurchaseDeliveryMode.DIRECT_TO_EVENT,
                ),
                admin,
            ),
        )
        _expect_http_error(
            400,
            lambda: create_purchase_request_from_order(
                db,
                partial_order.id,
                PurchaseRequestFromOrderCreate(
                    title="QA bodega incorrecta bloqueada",
                    delivery_mode=PurchaseDeliveryMode.TO_WAREHOUSE,
                    warehouse_id=other_warehouse.id,
                ),
                admin,
            ),
        )
        results.append("Compra vinculada: bloquea entrega directa y bodega diferente")

        purchase = create_purchase_request_from_order(
            db,
            partial_order.id,
            PurchaseRequestFromOrderCreate(
                title=f"QA compra faltante {marker}",
                delivery_mode=PurchaseDeliveryMode.TO_WAREHOUSE,
                warehouse_id=warehouse.id,
            ),
            admin,
        )
        _assert_decimal(purchase.items[0].quantity_requested, "5", "Purchase missing quantity")
        _expect_http_error(409, lambda: cancel_logistics_order(db, partial_order.id, admin))
        results.append("Cancelacion: bloqueada mientras existe una compra activa")

        purchase = approve_purchase_request(db, purchase.id, admin)
        purchase = mark_purchase_request_purchased(
            db,
            purchase.id,
            PurchaseRequestMarkPurchased(
                items=[
                    PurchaseRequestMarkPurchasedItem(
                        purchase_request_item_id=purchase.items[0].id,
                        quantity_purchased=Decimal("5"),
                        unit_price_purchased=Decimal("1000"),
                    )
                ]
            ),
            admin,
        )
        purchase = receive_purchase_request(
            db,
            purchase.id,
            PurchaseRequestReceive(
                items=[
                    PurchaseRequestReceiveItem(
                        purchase_request_item_id=purchase.items[0].id,
                        quantity_received=Decimal("5"),
                    )
                ]
            ),
            admin,
        )
        if purchase.status != PurchaseRequestStatus.RECEIVED:
            raise AssertionError(f"Purchase ended in {purchase.status}")
        partial_order = reserve_logistics_order_stock(db, partial_order.id, admin)
        if partial_order.status != LogisticsOrderStatus.RESERVED:
            raise AssertionError(f"Completed order ended in {partial_order.status}")
        _assert_decimal(partial_order.items[0].quantity_reserved, "8", "Completed reservation")
        results.append("Compra recibida: ingresa 5 a bodega y completa la reserva de 8")

        partial_order = cancel_logistics_order(db, partial_order.id, admin)
        partial_stock = db.scalar(
            select(StockBalance).where(
                StockBalance.warehouse_id == warehouse.id,
                StockBalance.item_id == partial_item.id,
            )
        )
        if partial_order.status != LogisticsOrderStatus.CANCELLED or not partial_stock:
            raise AssertionError("The completed partial order was not cancelled correctly")
        _assert_decimal(partial_stock.quantity_on_hand, "8", "Stock after purchase receipt")
        _assert_decimal(partial_stock.quantity_reserved, "0", "Released completed reservation")
        results.append("Cancelacion final: conserva stock fisico 8 y deja reservado en 0")

        transfer_item = _create_item_and_stock(
            db,
            marker=marker,
            suffix="transferencia",
            warehouse=warehouse,
            quantity="0",
        )
        source_stock = StockBalance(
            warehouse_id=other_warehouse.id,
            item_id=transfer_item.id,
            quantity_on_hand=Decimal("6"),
            quantity_reserved=Decimal("0"),
            quantity_damaged=Decimal("0"),
        )
        db.add(source_stock)
        db.flush()
        transfer_order = _create_order(
            db,
            marker=marker,
            suffix="transferencia",
            event=event,
            warehouse=warehouse,
            operator=operator,
            admin=admin,
            item=transfer_item,
            quantity="4",
        )
        availability = get_logistics_order_stock_availability(db, transfer_order.id, admin)
        transfer_availability = availability.items[0]
        source_row = next(
            row for row in transfer_availability.warehouses if row.warehouse_id == other_warehouse.id
        )
        _assert_decimal(source_row.available_quantity, "6", "Other warehouse availability")
        if not source_row.can_transfer:
            raise AssertionError("Admin should be allowed to transfer from the source warehouse")
        _expect_http_error(
            400,
            lambda: transfer_stock_to_logistics_order(
                db,
                transfer_order.id,
                LogisticsOrderStockTransferCreate(
                    logistics_order_item_id=transfer_order.items[0].id,
                    source_warehouse_id=other_warehouse.id,
                    quantity=Decimal("5"),
                ),
                admin,
            ),
        )
        transfer_order = transfer_stock_to_logistics_order(
            db,
            transfer_order.id,
            LogisticsOrderStockTransferCreate(
                logistics_order_item_id=transfer_order.items[0].id,
                source_warehouse_id=other_warehouse.id,
                quantity=Decimal("4"),
                notes="Prueba reversible",
            ),
            admin,
        )
        destination_stock = db.scalar(
            select(StockBalance).where(
                StockBalance.warehouse_id == warehouse.id,
                StockBalance.item_id == transfer_item.id,
            )
        )
        db.refresh(source_stock)
        if not destination_stock:
            raise AssertionError("Destination stock was not created")
        _assert_decimal(source_stock.quantity_on_hand, "2", "Source after transfer")
        _assert_decimal(destination_stock.quantity_on_hand, "4", "Destination after transfer")
        movement_types = set(
            db.scalars(
                select(StockMovement.movement_type).where(
                    StockMovement.reference_id == transfer_order.id,
                    StockMovement.movement_type.in_(
                        [StockMovementType.TRANSFER_OUT, StockMovementType.TRANSFER_IN]
                    ),
                )
            ).all()
        )
        if movement_types != {StockMovementType.TRANSFER_OUT, StockMovementType.TRANSFER_IN}:
            raise AssertionError(f"Transfer movements are incomplete: {movement_types}")
        transfer_order = reserve_logistics_order_stock(db, transfer_order.id, admin)
        if transfer_order.status != LogisticsOrderStatus.RESERVED:
            raise AssertionError("Transferred stock did not complete the order reservation")
        transfer_order = cancel_logistics_order(db, transfer_order.id, admin)
        if transfer_order.status != LogisticsOrderStatus.CANCELLED:
            raise AssertionError("Transferred order could not be cancelled")
        results.append("Multibodega: muestra 6, transfiere 4, registra OUT/IN y permite reservar")

        split_item = _create_item_and_stock(
            db,
            marker=marker,
            suffix="division",
            warehouse=warehouse,
            quantity="2",
        )
        split_order = _create_order(
            db,
            marker=marker,
            suffix="division",
            event=event,
            warehouse=warehouse,
            operator=operator,
            admin=admin,
            item=split_item,
            quantity="5",
        )
        split_order = reserve_logistics_order_stock(db, split_order.id, admin)
        split_request = create_partial_dispatch_request(
            db,
            split_order.id,
            LogisticsPartialDispatchRequestCreate(reason="El evento requiere despacho inmediato"),
            admin,
        )
        if split_request.status != "PENDING":
            raise AssertionError("Partial dispatch request was not created as PENDING")
        split_result = approve_partial_dispatch_request(
            db,
            split_request.id,
            LogisticsPartialDispatchReview(review_notes="Aprobado en prueba reversible"),
            admin,
        )
        if split_result.dispatch_order.status != LogisticsOrderStatus.RESERVED:
            raise AssertionError("Available order was not ready for preparation")
        if split_result.pending_order.status != LogisticsOrderStatus.ASSIGNED:
            raise AssertionError("Pending child order was not assigned")
        if split_result.pending_order.parent_order_id != split_result.dispatch_order.id:
            raise AssertionError("Pending child order was not linked to its parent")
        _assert_decimal(split_result.dispatch_order.items[0].quantity_requested, "2", "Dispatch split quantity")
        _assert_decimal(split_result.pending_order.items[0].quantity_requested, "3", "Pending split quantity")
        cancel_logistics_order(db, split_result.dispatch_order.id, admin)
        cancel_logistics_order(db, split_result.pending_order.id, admin)
        results.append("Despacho parcial: aprobación divide 2 disponibles y 3 pendientes sin duplicar stock")
    finally:
        db.close()
        if outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()

    with SessionLocal() as verification_db:
        persisted = verification_db.scalar(
            select(func.count()).select_from(InventoryItem).where(InventoryItem.sku.like(f"QA-{marker}-%"))
        )
        if persisted:
            raise AssertionError(f"Rollback failed: {persisted} QA inventory records persisted")
    results.append("Rollback: no quedaron datos QA en la base")
    return results


if __name__ == "__main__":
    checks = run_verification()
    print("VERIFICACION LOGISTICA: OK")
    for check in checks:
        print(f"- {check}")
