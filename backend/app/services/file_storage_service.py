from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

EVIDENCE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}
CSV_CONTENT_TYPES = {"text/csv": ".csv"}
UPLOAD_ROOT = Path("uploads")


def save_evidence_file(file: UploadFile) -> tuple[str, str]:
    return save_upload_file("evidences", file, EVIDENCE_CONTENT_TYPES)


def save_order_evidence_file(folder: str, file: UploadFile) -> tuple[str, str, int]:
    content_type = file.content_type or "application/octet-stream"
    extension = EVIDENCE_CONTENT_TYPES.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type",
        )
    content = _read_upload_file(file)
    file_url = _save_content(
        folder=folder,
        content=content,
        content_type=content_type,
        extension=extension,
        original_filename=file.filename,
    )
    return file_url, content_type, len(content)


def save_survey_import_file(filename: str, content: bytes) -> str:
    return save_bytes_file(
        "surveys",
        content,
        content_type="text/csv",
        allowed_content_types=CSV_CONTENT_TYPES,
        original_filename=filename or "google-sheets-export.csv",
    )


def save_upload_file(
    folder: str,
    file: UploadFile,
    allowed_content_types: dict[str, str],
) -> tuple[str, str]:
    content_type = file.content_type or "application/octet-stream"
    extension = allowed_content_types.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type",
        )
    content = _read_upload_file(file)
    file_url = _save_content(
        folder=folder,
        content=content,
        content_type=content_type,
        extension=extension,
    )
    return file_url, content_type


def save_bytes_file(
    folder: str,
    content: bytes,
    *,
    content_type: str,
    allowed_content_types: dict[str, str],
    original_filename: str | None = None,
) -> str:
    extension = allowed_content_types.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type",
        )
    _ensure_allowed_size(len(content))
    return _save_content(
        folder=folder,
        content=content,
        content_type=content_type,
        extension=extension,
        original_filename=original_filename,
    )


def delete_stored_file(file_url: str) -> None:
    if settings.use_r2_storage:
        _delete_from_r2(file_url)
        return

    path = Path(file_url)
    try:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    except OSError:
        return


def _read_upload_file(file: UploadFile) -> bytes:
    content = file.file.read(settings.max_upload_size_bytes + 1)
    _ensure_allowed_size(len(content))
    return content


def _ensure_allowed_size(size: int) -> None:
    if size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_size_mb} MB limit",
        )


def _save_content(
    *,
    folder: str,
    content: bytes,
    content_type: str,
    extension: str,
    original_filename: str | None = None,
) -> str:
    filename = _build_filename(extension, original_filename)
    key = f"{folder}/{filename}"
    if settings.use_r2_storage:
        return _save_to_r2(key, content, content_type)

    upload_dir = UPLOAD_ROOT / folder
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / filename
    destination.write_bytes(content)
    return destination.as_posix()


def _build_filename(extension: str, original_filename: str | None = None) -> str:
    if not original_filename:
        return f"{uuid4()}{extension}"
    safe_name = Path(original_filename).name
    if not safe_name.lower().endswith(extension):
        safe_name = f"{safe_name}{extension}"
    return f"{uuid4()}-{safe_name}"


def _r2_client():
    import boto3

    endpoint_url = f"https://{settings.cloudflare_r2_account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.cloudflare_r2_access_key_id,
        aws_secret_access_key=settings.cloudflare_r2_secret_access_key,
        region_name="auto",
    )


def _save_to_r2(key: str, content: bytes, content_type: str) -> str:
    _r2_client().put_object(
        Bucket=settings.cloudflare_r2_bucket,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    public_base_url = str(settings.cloudflare_r2_public_base_url).rstrip("/")
    return f"{public_base_url}/{key}"


def _delete_from_r2(file_url: str) -> None:
    public_base_url = str(settings.cloudflare_r2_public_base_url).rstrip("/")
    if not file_url.startswith(f"{public_base_url}/"):
        return
    key = file_url.removeprefix(f"{public_base_url}/")
    try:
        _r2_client().delete_object(Bucket=settings.cloudflare_r2_bucket, Key=key)
    except Exception:
        return
