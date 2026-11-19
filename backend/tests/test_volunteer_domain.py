from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.volunteer_schema import ContributionCreate, ContributionItemCreate, PublicVolunteerRegistration
from app.services import volunteer_service
from app.services import volunteer_email_service


def test_email_normalization_deduplicates_case_and_whitespace() -> None:
    assert volunteer_service.normalize_email("  Maria.Perez@Example.COM ") == "maria.perez@example.com"
    assert volunteer_service.email_lookup_hash("Maria.Perez@Example.COM") == volunteer_service.email_lookup_hash(" maria.perez@example.com ")


def test_phone_normalization_keeps_only_digits() -> None:
    assert volunteer_service.normalize_phone("+56 9 1234-5678") == "56912345678"
    assert volunteer_service.normalize_phone(None) is None


def test_contribution_total_sums_decimal_items_to_milligrams_precision() -> None:
    assert volunteer_service.calculate_contribution_total([
        Decimal("2.3454"), Decimal("4.200"), Decimal("1.005"),
    ]) == Decimal("7.550")


@pytest.mark.parametrize("weight", [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), Decimal("1000000.001")])
def test_invalid_contribution_weight_is_rejected(weight: Decimal) -> None:
    with pytest.raises(ValueError):
        volunteer_service.calculate_contribution_total([weight])


def test_duplicate_materials_in_one_delivery_are_rejected() -> None:
    material_id = uuid4()
    with pytest.raises(ValueError):
        ContributionCreate(
            volunteer_id=uuid4(),
            items=[
                ContributionItemCreate(material_id=material_id, weight_kg=Decimal("1")),
                ContributionItemCreate(material_id=material_id, weight_kg=Decimal("2")),
            ],
        )


def test_public_registration_requires_explicit_consent() -> None:
    with pytest.raises(ValueError):
        PublicVolunteerRegistration(
            activation_slug="a" * 24,
            full_name="Maria Perez",
            email="maria@example.com",
            phone="+56 9 1234 5678",
            consent_accepted=False,
        )


def test_contribution_email_escapes_personal_content(monkeypatch) -> None:
    captured: dict = {}

    def fake_deliver(payload: dict):
        captured.update(payload)
        return True, None

    monkeypatch.setattr(volunteer_email_service, "_deliver", fake_deliver)
    sent, error = volunteer_email_service.send_contribution_email({
        "recipient": "maria@example.com",
        "volunteer_name": "<María>",
        "activation_name": "Temuco & Plaza",
        "event_name": "Evento <QA>",
        "items": [{"material": "PET", "weight_kg": Decimal("2.500")}],
        "total_weight_kg": Decimal("2.500"),
        "accumulated_weight_kg": Decimal("8.750"),
        "impact_url": "https://example.test/public/mi-aporte/secret-token",
    })
    assert sent is True and error is None
    assert "&lt;María&gt;" in captured["html"]
    assert "Evento &lt;QA&gt;" in captured["html"]
    assert "secret-token" in captured["text"]
