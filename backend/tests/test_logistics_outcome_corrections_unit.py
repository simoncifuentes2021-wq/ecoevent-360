from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase

from fastapi import HTTPException

from app.services.logistics_order_service import _corrected_stock_quantities


class LogisticsOutcomeCorrectionTests(TestCase):
    def test_allows_returned_consumable_to_be_reclassified_as_consumed(self):
        stock = SimpleNamespace(
            quantity_on_hand=Decimal("1"),
            quantity_reserved=Decimal("0"),
            quantity_damaged=Decimal("0"),
        )

        on_hand, damaged = _corrected_stock_quantities(
            stock,
            delta_returned=Decimal("-1"),
            delta_returned_damaged=Decimal("0"),
        )

        self.assertEqual(on_hand, Decimal("0"))
        self.assertEqual(damaged, Decimal("0"))

    def test_allows_damaged_return_to_be_corrected(self):
        stock = SimpleNamespace(
            quantity_on_hand=Decimal("2"),
            quantity_reserved=Decimal("0"),
            quantity_damaged=Decimal("1"),
        )

        on_hand, damaged = _corrected_stock_quantities(
            stock,
            delta_returned=Decimal("0"),
            delta_returned_damaged=Decimal("-1"),
        )

        self.assertEqual(on_hand, Decimal("1"))
        self.assertEqual(damaged, Decimal("0"))

    def test_rejects_correction_when_returned_stock_is_already_reserved(self):
        stock = SimpleNamespace(
            quantity_on_hand=Decimal("1"),
            quantity_reserved=Decimal("1"),
            quantity_damaged=Decimal("0"),
        )

        with self.assertRaises(HTTPException) as error:
            _corrected_stock_quantities(
                stock,
                delta_returned=Decimal("-1"),
                delta_returned_damaged=Decimal("0"),
            )

        self.assertEqual(error.exception.status_code, 409)
