from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
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

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4()}{extension}"
    destination = UPLOAD_DIR / filename

    with destination.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            output.write(chunk)

    return destination.as_posix(), content_type


def delete_local_file(file_url: str) -> None:
    path = Path(file_url)
    try:
        if path.is_file() and UPLOAD_DIR.resolve() in path.resolve().parents:
            path.unlink()
    except OSError:
        # The database record is the source of truth; file cleanup can be retried later.
        return
