from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException

from app.core.config import settings
from app.services.file_storage_service import (
    read_private_object_from_r2,
    save_private_object_to_r2,
)


class DocumentStorageProvider(Protocol):
    def store(
        self, document_id: UUID, version: int, variant: str, content: bytes
    ) -> tuple[str, str]: ...
    def read(self, reference: str) -> bytes: ...


class LocalPrivateDocumentStorage:
    """Immutable PDF storage isolated from R2 and public web roots."""

    def _path(self, reference: str) -> Path:
        root = Path(settings.local_private_storage_root).resolve()
        path = (root / reference).resolve()
        if root not in path.parents or path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=404, detail="El PDF no está disponible")
        return path

    def store(
        self, document_id: UUID, version: int, variant: str, content: bytes
    ) -> tuple[str, str]:
        if variant not in {"original", "signed"} or not content.startswith(b"%PDF-"):
            raise ValueError("Invalid document artifact")
        root = Path(settings.local_private_storage_root).resolve()
        path = self._path(f"documents/{document_id}/v{version}-{variant}.pdf")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise HTTPException(status_code=409, detail="Este PDF inmutable ya existe")
        path.write_bytes(content)
        key = path.relative_to(root).as_posix()
        return key, hashlib.sha256(content).hexdigest()

    def read(self, reference: str) -> bytes:
        path = self._path(reference)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="El PDF no está disponible")
        return path.read_bytes()


class CloudflareR2PrivateDocumentStorage:
    """Private immutable document PDFs stored in Cloudflare R2."""

    def store(
        self, document_id: UUID, version: int, variant: str, content: bytes
    ) -> tuple[str, str]:
        if variant not in {"original", "signed"} or not content.startswith(b"%PDF-"):
            raise ValueError("Invalid document artifact")
        prefix = settings.r2_private_prefix.strip("/")
        key = f"{prefix}/documents/{document_id}/v{version}-{variant}.pdf"
        save_private_object_to_r2(key, content, content_type="application/pdf")
        return key, hashlib.sha256(content).hexdigest()

    def read(self, reference: str) -> bytes:
        content, _ = read_private_object_from_r2(reference)
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=404, detail="El PDF no está disponible")
        return content


class ConfiguredPrivateDocumentStorage:
    """Routes new artifacts to R2 when requested and keeps legacy local PDFs readable."""

    def __init__(self) -> None:
        self.local = LocalPrivateDocumentStorage()
        self.r2 = CloudflareR2PrivateDocumentStorage()

    def store(
        self, document_id: UUID, version: int, variant: str, content: bytes
    ) -> tuple[str, str]:
        if settings.use_r2_storage or settings.documents_use_r2_storage:
            if not settings.cloudflare_r2_configured:
                raise RuntimeError("DOCUMENTS_USE_R2_STORAGE requiere credenciales Cloudflare R2")
            return self.r2.store(document_id, version, variant, content)
        return self.local.store(document_id, version, variant, content)

    def read(self, reference: str) -> bytes:
        r2_prefix = f"{settings.r2_private_prefix.strip('/')}/documents/"
        if reference.replace("\\", "/").startswith(r2_prefix):
            return self.r2.read(reference)
        # Keep PDFs created before R2 was enabled readable during migration.
        return self.local.read(reference)


document_storage: DocumentStorageProvider = ConfiguredPrivateDocumentStorage()
