from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.models.enums import LogisticsOrderStatus, PurchaseDeliveryMode
from app.schemas.logistics_order_schema import LogisticsOrderUpdate
from app.schemas.stock_schema import StockMovementCreate
from app.services.logistics_order_service import CANCELLABLE_STATUSES, _quantity_to_reserve
from app.services.purchase_request_service import _ensure_linked_purchase_destination


class LogisticsFlowRulesTests(TestCase):
    def test_partial_reservation_takes_only_available_stock(self):
        self.assertEqual(
            _quantity_to_reserve(Decimal("10"), Decimal("2"), Decimal("3")),
            Decimal("3"),
        )

    def test_partial_reservation_only_tops_up_remaining_quantity(self):
        self.assertEqual(
            _quantity_to_reserve(Decimal("10"), Decimal("8"), Decimal("7")),
            Decimal("2"),
        )

    def test_update_schema_rejects_manual_status_changes(self):
        with self.assertRaises(ValidationError):
            LogisticsOrderUpdate.model_validate({"status": "CANCELLED"})

    def test_order_cannot_be_cancelled_after_dispatch(self):
        self.assertNotIn(LogisticsOrderStatus.OUT_OF_WAREHOUSE, CANCELLABLE_STATUSES)
        self.assertNotIn(LogisticsOrderStatus.CLOSED, CANCELLABLE_STATUSES)

    def test_linked_purchase_must_enter_order_warehouse(self):
        warehouse_id = uuid4()
        order = SimpleNamespace(warehouse_id=warehouse_id)

        _ensure_linked_purchase_destination(order, PurchaseDeliveryMode.TO_WAREHOUSE, warehouse_id)

        with self.assertRaises(HTTPException):
            _ensure_linked_purchase_destination(order, PurchaseDeliveryMode.TO_WAREHOUSE, uuid4())
        with self.assertRaises(HTTPException):
            _ensure_linked_purchase_destination(order, PurchaseDeliveryMode.DIRECT_TO_EVENT, None)

    def test_transfer_movements_cannot_be_created_as_manual_adjustments(self):
        with self.assertRaises(ValidationError):
            StockMovementCreate.model_validate(
                {
                    "warehouse_id": str(uuid4()),
                    "item_id": str(uuid4()),
                    "movement_type": "TRANSFER_IN",
                    "quantity": 1,
                }
            )
