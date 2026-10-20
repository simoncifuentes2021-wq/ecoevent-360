from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol


@dataclass(frozen=True)
class SignatureCapability:
    token: str
    token_hash: str
    expires_at: datetime


class SignatureProvider(Protocol):
    name: str

    def create_signature_request(self, now: datetime, ttl: timedelta) -> SignatureCapability: ...


class LocalSimulatedSignatureProvider:
    """Development adapter; records an explicit simulated signature, never legal e-signature."""

    name = "LOCAL_SIMULATED"

    def create_signature_request(self, now: datetime, ttl: timedelta) -> SignatureCapability:
        token = secrets.token_urlsafe(40)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return SignatureCapability(token=token, token_hash=token_hash, expires_at=now + ttl)


signature_provider: SignatureProvider = LocalSimulatedSignatureProvider()
