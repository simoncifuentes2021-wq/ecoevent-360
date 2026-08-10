"""Private object storage with local and Cloudflare R2 backends.

Database values created by this module are opaque storage keys.  Absolute URLs and
old ``uploads/...`` paths remain readable during the controlled legacy migration.
"""

from __future__ import annotations

import csv
import io
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

IMAGE_CONTENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
EVIDENCE_CONTENT_TYPES = {**IMAGE_CONTENT_TYPES, "application/pdf": ".pdf"}
CSV_CONTENT_TYPES = {"text/csv": ".csv"}
_KEY_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class StoredObject:
    content: bytes
    content_type: str
    size: int


def validate_storage_key(key: str, *, allowed_prefix: str | None = None) -> str:
    if not key or "\\" in key or key.startswith(("/", "~")):
        raise ValueError("Invalid storage key")
    path = PurePosixPath(key)
    if any(part in {"", ".", ".."} or not _KEY_PART.fullmatch(part) for part in path.parts):
        raise ValueError("Invalid storage key")
    if allowed_prefix and path.parts[0] != allowed_prefix.strip("/"):
        raise ValueError("Storage key outside allowed prefix")
    return path.as_posix()


def sanitize_filename(value: str | None, default: str = "archivo") -> str:
    name = Path(value or default).name.replace('"', "").replace("\r", "").replace("\n", "")
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return (name or default)[:180]


def save_evidence_file(file: UploadFile) -> tuple[str, str]:
    content = _read_upload_file(file)
    mime, extension = _validate_image(content)
    return _save_content("evidences", content, mime, extension), mime


def save_order_evidence_file(folder: str, file: UploadFile) -> tuple[str, str, int]:
    content = _read_upload_file(file)
    claimed = file.content_type or "application/octet-stream"
    if claimed == "application/pdf":
        if not content.startswith(b"%PDF-"):
            _bad_file("Invalid PDF content")
        mime, extension = "application/pdf", ".pdf"
    else:
        mime, extension = _validate_image(content)
    return _save_content(folder, content, mime, extension), mime, len(content)


def save_survey_import_file(filename: str, content: bytes) -> str:
    _ensure_allowed_size(len(content))
    try:
        text = content.decode("utf-8-sig")
        next(csv.reader(io.StringIO(text)), None)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid CSV content") from exc
    return _save_content("surveys", content, "text/csv", ".csv")


def save_upload_file(
    folder: str, file: UploadFile, allowed_content_types: dict[str, str]
) -> tuple[str, str]:
    content = _read_upload_file(file)
    if set(allowed_content_types).issubset(IMAGE_CONTENT_TYPES):
        mime, extension = _validate_image(content)
        if mime not in allowed_content_types:
            _bad_file("Unsupported file type")
    else:
        mime = file.content_type or "application/octet-stream"
        extension = allowed_content_types.get(mime)
        if not extension:
            _bad_file("Unsupported file type")
    return _save_content(folder, content, mime, extension), mime


def save_bytes_file(
    folder: str,
    content: bytes,
    *,
    content_type: str,
    allowed_content_types: dict[str, str],
    original_filename: str | None = None,
) -> str:
    _ensure_allowed_size(len(content))
    extension = allowed_content_types.get(content_type)
    if not extension:
        _bad_file("Unsupported file type")
    return _save_content(folder, content, content_type, extension)


def save_private_object(key: str, content: bytes, *, content_type: str) -> str:
    """Store immutable server-generated content at an explicit private key."""
    _ensure_allowed_size(len(content))
    prefix = settings.r2_private_prefix.strip("/")
    normalized = validate_storage_key(key, allowed_prefix=prefix)
    if settings.use_r2_storage:
        _r2_client().put_object(
            Bucket=settings.cloudflare_r2_bucket,
            Key=normalized,
            Body=content,
            ContentType=content_type,
            CacheControl="private, no-store",
        )
    else:
        destination = _local_path(normalized)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError("Immutable object already exists")
        destination.write_bytes(content)
    return normalized


def read_stored_file(reference: str) -> tuple[bytes, str]:
    obj = get_stored_object(reference)
    return obj.content, obj.content_type


def get_stored_object(reference: str) -> StoredObject:
    key = legacy_reference_to_key(reference)
    if settings.use_r2_storage:
        try:
            response = _r2_client().get_object(Bucket=settings.cloudflare_r2_bucket, Key=key)
            content = response["Body"].read()
            mime = (
                response.get("ContentType")
                or mimetypes.guess_type(key)[0]
                or "application/octet-stream"
            )
            return StoredObject(content, mime, len(content))
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Stored file not found") from exc
    path = _local_path(key, allow_legacy=True)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored file not found")
    content = path.read_bytes()
    return StoredObject(
        content, mimetypes.guess_type(path.name)[0] or "application/octet-stream", len(content)
    )


def stored_file_exists(reference: str) -> bool:
    try:
        get_stored_object(reference)
        return True
    except (HTTPException, ValueError):
        return False


def generate_temporary_download(reference: str, expires: int | None = None) -> str | None:
    if not settings.use_r2_storage:
        return None
    key = legacy_reference_to_key(reference)
    return _r2_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.cloudflare_r2_bucket, "Key": key},
        ExpiresIn=expires or settings.r2_signed_url_expires_seconds,
    )


def delete_stored_file(reference: str) -> None:
    try:
        key = legacy_reference_to_key(reference)
        if settings.use_r2_storage:
            _r2_client().delete_object(Bucket=settings.cloudflare_r2_bucket, Key=key)
        else:
            path = _local_path(key, allow_legacy=True)
            if path.is_file():
                path.unlink()
    except (OSError, ValueError):
        return


def legacy_reference_to_key(reference: str) -> str:
    value = (reference or "").strip()
    public = str(settings.cloudflare_r2_public_base_url or "").rstrip("/")
    if public and value.startswith(public + "/"):
        value = unquote(value[len(public) + 1 :])
    elif value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        value = unquote(parsed.path.lstrip("/"))
    value = value.replace("\\", "/")
    if value.startswith("/uploads/"):
        value = value[1:]
    if value.startswith("uploads/"):
        value = value[len("uploads/") :]
    # New keys are private/<category>/<uuid.ext>; legacy keys are category/name.
    allowed = settings.r2_private_prefix.strip("/")
    if value.startswith(allowed + "/"):
        return validate_storage_key(value, allowed_prefix=allowed)
    return validate_storage_key(value)


def _save_content(folder: str, content: bytes, content_type: str, extension: str) -> str:
    _ensure_allowed_size(len(content))
    folder = validate_storage_key(folder)
    prefix = settings.r2_private_prefix.strip("/")
    key = validate_storage_key(f"{prefix}/{folder}/{uuid4().hex}{extension}", allowed_prefix=prefix)
    if settings.use_r2_storage:
        _r2_client().put_object(
            Bucket=settings.cloudflare_r2_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            CacheControl="no-store",
        )
    else:
        destination = _local_path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    return key


def _local_path(key: str, *, allow_legacy: bool = False) -> Path:
    normalized = validate_storage_key(key)
    private_root = Path(settings.local_private_storage_root).resolve()
    prefix = settings.r2_private_prefix.strip("/") + "/"
    relative = normalized[len(prefix) :] if normalized.startswith(prefix) else normalized
    root = private_root if normalized.startswith(prefix) else Path("uploads").resolve()
    if root != private_root and not allow_legacy:
        raise ValueError("Legacy path is read-only")
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise ValueError("Storage path traversal")
    return target


def _validate_image(content: bytes) -> tuple[str, str]:
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            pixels = image.width * image.height
            if pixels > settings.max_image_pixels:
                _bad_file("Image dimensions exceed limit")
            fmt = (image.format or "").upper()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=400, detail="Invalid or corrupt image") from exc
    mapping = {
        "JPEG": ("image/jpeg", ".jpg"),
        "PNG": ("image/png", ".png"),
        "WEBP": ("image/webp", ".webp"),
    }
    if fmt not in mapping:
        _bad_file("Unsupported image format")
    return mapping[fmt]


def _read_upload_file(file: UploadFile) -> bytes:
    content = file.file.read(settings.max_upload_size_bytes + 1)
    _ensure_allowed_size(len(content))
    if not content:
        _bad_file("File cannot be empty")
    return content


def _ensure_allowed_size(size: int) -> None:
    if size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_size_mb} MB limit",
        )


def _bad_file(detail: str):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _r2_client():
    import boto3

    endpoint = (
        settings.cloudflare_r2_endpoint
        or f"https://{settings.cloudflare_r2_account_id}.r2.cloudflarestorage.com"
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.cloudflare_r2_access_key_id,
        aws_secret_access_key=settings.cloudflare_r2_secret_access_key,
        region_name=settings.cloudflare_r2_region,
    )
