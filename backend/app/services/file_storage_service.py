from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/pdf": ".pdf",
    "text/csv": ".csv",
}
UPLOAD_DIR = Path("uploads/evidences")


def save_evidence_file(file: UploadFile) -> tuple[str, str]:
    content_type = file.content_type or "application/octet-stream"
    extension = ALLOWED_CONTENT_TYPES.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type",
        )

    if settings.use_r2_storage:
        return _save_to_r2(file, extension, content_type)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4()}{extension}"
    destination = UPLOAD_DIR / filename

    with destination.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            output.write(chunk)

    return destination.as_posix(), content_type


def delete_local_file(file_url: str) -> None:
    if settings.use_r2_storage:
        _delete_from_r2(file_url)
        return

    path = Path(file_url)
    try:
        if path.is_file() and UPLOAD_DIR.resolve() in path.resolve().parents:
            path.unlink()
    except OSError:
        # The database record is the source of truth; file cleanup can be retried later.
        return


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


def _save_to_r2(file: UploadFile, extension: str, content_type: str) -> tuple[str, str]:
    filename = f"evidences/{uuid4()}{extension}"
    _r2_client().upload_fileobj(
        file.file,
        settings.cloudflare_r2_bucket,
        filename,
        ExtraArgs={"ContentType": content_type},
    )
    public_base_url = str(settings.cloudflare_r2_public_base_url).rstrip("/")
    return f"{public_base_url}/{filename}", content_type


def _delete_from_r2(file_url: str) -> None:
    public_base_url = str(settings.cloudflare_r2_public_base_url).rstrip("/")
    if not file_url.startswith(f"{public_base_url}/"):
        return
    key = file_url.removeprefix(f"{public_base_url}/")
    try:
        _r2_client().delete_object(Bucket=settings.cloudflare_r2_bucket, Key=key)
    except Exception:
        return
