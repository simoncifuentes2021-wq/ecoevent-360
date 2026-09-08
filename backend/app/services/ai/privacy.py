import re
from typing import Any

SENSITIVE_KEYS = {"email", "phone", "telephone", "contact", "address", "rut", "dni", "password", "token", "secret", "full_name", "first_name", "last_name", "participant", "responder", "user_id", "private_url", "storage_url", "responses"}
PATTERNS = (
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[EMAIL]"),
    # Dots bound decimal measurements (31.68000000) and must never turn their
    # last eight digits into a phone redaction marker.
    (re.compile(r"(?<![\w.-])(?:\+?56\s*)?(?:9\s*)?\d{4}[\s-]?\d{4}(?![\w.-])"), "[PHONE]"),
    (re.compile(r"(?<!\w)\d{1,2}\.\d{3}\.\d{3}-[0-9Kk](?!\w)"), "[DOCUMENT_ID]"),
    (re.compile(r"https?://[^\s]+(?:token|signature|sig|key|private)[^\s]*", re.I), "[PRIVATE_URL]"),
    (re.compile(r"\b(?:sk-|Bearer\s+)[A-Za-z0-9._-]{16,}\b", re.I), "[SECRET]"),
)


def sanitize_text(value: str) -> str:
    for pattern, replacement in PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize(child) for key, child in value.items() if not any(token in key.lower() for token in SENSITIVE_KEYS)}
    if isinstance(value, list):
        return [sanitize(child) for child in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value
