import io
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image
from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.config import settings
from app.core.rate_limit import RateLimiter, client_ip
from app.services import file_storage_service
from app.services.file_storage_service import (
    legacy_reference_to_key,
    read_stored_file,
    save_evidence_file,
    save_private_object,
    validate_storage_key,
)


def upload(name: str, content: bytes, claimed: str) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content), headers=Headers({"content-type": claimed}))


def image_bytes(fmt="PNG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(buffer, format=fmt)
    return buffer.getvalue()


def test_private_image_storage_validates_content_and_mime(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_r2_bucket", None)
    monkeypatch.setattr(settings, "cloudflare_r2_account_id", None)
    monkeypatch.setattr(settings, "cloudflare_r2_access_key_id", None)
    monkeypatch.setattr(settings, "cloudflare_r2_secret_access_key", None)
    root = Path(".tmp") / f"security-storage-{uuid4().hex}"
    monkeypatch.setattr(settings, "local_private_storage_root", str(root))
    try:
        key, mime = save_evidence_file(upload("false-extension.pdf", image_bytes("PNG"), "application/pdf"))
        assert key.startswith("private/evidences/")
        assert mime == "image/png"
        content, served_mime = read_stored_file(key)
        assert content.startswith(b"\x89PNG")
        assert served_mime == "image/png"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_evidences_and_report_publications_share_the_same_r2_backend(monkeypatch):
    objects: dict[str, tuple[bytes, str]] = {}
    calls: list[tuple[str, str, str]] = []

    class FakeR2:
        def put_object(self, *, Bucket, Key, Body, ContentType, **_kwargs):
            calls.append(("put", Bucket, Key))
            objects[Key] = (Body, ContentType)

        def get_object(self, *, Bucket, Key):
            calls.append(("get", Bucket, Key))
            content, content_type = objects[Key]
            return {"Body": io.BytesIO(content), "ContentType": content_type}

    monkeypatch.setattr(settings, "force_local_storage", False)
    monkeypatch.setattr(settings, "cloudflare_r2_bucket", "production-compatible-bucket")
    monkeypatch.setattr(settings, "cloudflare_r2_account_id", "account")
    monkeypatch.setattr(settings, "cloudflare_r2_access_key_id", "access")
    monkeypatch.setattr(settings, "cloudflare_r2_secret_access_key", "secret")
    monkeypatch.setattr(file_storage_service, "_r2_client", lambda: FakeR2())

    evidence_key, _ = save_evidence_file(upload("evidence.png", image_bytes(), "image/png"))
    report_key = save_private_object(
        "private/reports/event/report/publications/v1/report-test.pdf",
        b"%PDF-1.7\n%%EOF",
        content_type="application/pdf",
    )

    assert read_stored_file(evidence_key)[0].startswith(b"\x89PNG")
    assert read_stored_file(report_key) == (b"%PDF-1.7\n%%EOF", "application/pdf")
    assert {bucket for _, bucket, _ in calls} == {"production-compatible-bucket"}
    assert evidence_key.startswith("private/evidences/")
    assert report_key.startswith("private/reports/")


@pytest.mark.parametrize("content,claimed", [(b"not-an-image", "image/png"), (b"%PDF-1.7\n", "application/pdf")])
def test_photo_flow_rejects_corrupt_or_pdf(content, claimed):
    with pytest.raises(HTTPException) as exc:
        save_evidence_file(upload("photo.jpg", content, claimed))
    assert exc.value.status_code == 400


@pytest.mark.parametrize("key", ["../secret", "private/../secret", "/private/file", "private\\file"])
def test_storage_key_rejects_path_traversal(key):
    with pytest.raises(ValueError):
        validate_storage_key(key)


def test_legacy_references_convert_without_public_dependency(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_r2_public_base_url", "https://legacy.invalid")
    assert legacy_reference_to_key("uploads/evidences/file.jpg") == "evidences/file.jpg"
    assert legacy_reference_to_key("https://legacy.invalid/private/evidences/file.jpg") == "private/evidences/file.jpg"


def test_rate_limiter_returns_retry_after_with_redis():
    limiter = RateLimiter()
    identity = uuid4().hex
    limiter.check("certification", identity, "2/60")
    limiter.check("certification", identity, "2/60")
    with pytest.raises(HTTPException) as exc:
        limiter.check("certification", identity, "2/60")
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) > 0


def test_untrusted_forwarded_for_is_ignored(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_count", 0)
    request = Request({"type": "http", "client": ("127.0.0.1", 1234),
                       "headers": [(b"x-forwarded-for", b"203.0.113.10")]})
    assert client_ip(request) == "127.0.0.1"
