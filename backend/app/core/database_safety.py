"""Fail-closed guard for destructive/integration database test entry points."""
from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse


CONFIRMATION = "ecoevent-test-only"
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres", "postgres-certification"}
TEST_MARKERS = ("test", "ci", "disposable", "certification")


def _safe_parts(value: str, variable: str) -> tuple[str, str, str]:
    parsed = urlparse(value.replace("postgresql+psycopg://", "postgresql://", 1))
    host = (parsed.hostname or "").lower()
    database = parsed.path.lstrip("/").split("?", 1)[0]
    user = parsed.username or ""
    if not host or not database or not user:
        raise RuntimeError(f"{variable} is not a complete PostgreSQL URL")
    if "supabase" in host or "pooler" in host:
        raise RuntimeError(f"{variable} points to a forbidden remote provider")
    try:
        address = ipaddress.ip_address(host)
        local = address.is_loopback
    except ValueError:
        local = host in ALLOWED_HOSTS
    if not local:
        raise RuntimeError(f"{variable} host is not explicitly local/disposable")
    if not any(marker in database.lower() for marker in TEST_MARKERS):
        raise RuntimeError(f"{variable} database name is not marked disposable")
    return host, database, user


def require_disposable_database() -> dict[str, str]:
    if os.getenv("CI_DATABASE_CONFIRM") != CONFIRMATION:
        raise RuntimeError("CI_DATABASE_CONFIRM does not authorize a disposable test database")
    runtime = os.getenv("DATABASE_URL", "")
    migration = os.getenv("MIGRATION_DATABASE_URL", "")
    runtime_parts = _safe_parts(runtime, "DATABASE_URL")
    migration_parts = _safe_parts(migration, "MIGRATION_DATABASE_URL")
    if runtime_parts[:2] != migration_parts[:2]:
        raise RuntimeError("Runtime and migration URLs must target the same isolated database")
    return {"host": runtime_parts[0], "database": runtime_parts[1],
            "runtime_user": runtime_parts[2], "migration_user": migration_parts[2]}
