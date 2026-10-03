import base64

from app.services import bike_zone_email_service
from app.services.bike_zone_email_service import BikeZoneEmail


class FakeResponse:
    def raise_for_status(self):
        return None


class FakeClient:
    payload = None

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, *, headers, json):
        self.url = url
        self.headers = headers
        FakeClient.payload = json
        return FakeResponse()


def test_bike_zone_email_contains_code_link_and_inline_qr(monkeypatch):
    monkeypatch.setattr(bike_zone_email_service.httpx, "Client", FakeClient)
    monkeypatch.setattr(bike_zone_email_service.settings, "resend_api_key", "re_test")
    monkeypatch.setattr(
        bike_zone_email_service.settings,
        "email_from",
        "Greenway App <noreply@app.greenway.cl>",
    )
    monkeypatch.setattr(
        bike_zone_email_service.settings,
        "public_app_url",
        "https://app.greenway.cl",
    )

    bike_zone_email_service.send_bike_zone_email(
        BikeZoneEmail(
            recipient="bike@example.com",
            participant_name="Ana Pérez",
            event_name="WWE",
            session_name="Jornada 1",
            code="BZ-ABC123",
        )
    )

    payload = FakeClient.payload
    assert payload["to"] == ["bike@example.com"]
    assert payload["subject"] == "Tu código Bike Zone | Greenway App — WWE"
    assert payload["from"] == "Greenway App <noreply@app.greenway.cl>"
    assert "Greenway App" in payload["html"]
    assert "BZ-ABC123" in payload["html"]
    assert "https://app.greenway.cl/bike-zone/BZ-ABC123" in payload["html"]
    assert "cid:bike-zone-qr" in payload["html"]
    assert payload["attachments"][0]["content_id"] == "bike-zone-qr"
    assert base64.b64decode(payload["attachments"][0]["content"]).startswith(b"\x89PNG")


def test_bike_zone_email_skips_without_resend_key(monkeypatch):
    monkeypatch.setattr(bike_zone_email_service.settings, "resend_api_key", None)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Resend should not be called")

    monkeypatch.setattr(bike_zone_email_service.httpx, "Client", fail_if_called)
    bike_zone_email_service.send_bike_zone_email(
        BikeZoneEmail(
            recipient="bike@example.com",
            participant_name=None,
            event_name="WWE",
            session_name=None,
            code="BZ-ABC123",
        )
    )
