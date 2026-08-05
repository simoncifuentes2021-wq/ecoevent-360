"""Temporary, SUPER_ADMIN-only production database identity diagnostic."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.enums import UserRole


router = APIRouter(
    prefix="/internal/temporary/database-identity",
    tags=["temporary diagnostics"],
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)

_IDENTITY_QUERY = text(
    """
    SELECT
        current_user,
        current_database(),
        rolsuper,
        rolcreatedb,
        rolcreaterole,
        rolinherit,
        rolreplication,
        rolbypassrls
    FROM pg_roles
    WHERE rolname = current_user
    """
)


class DatabaseIdentity(BaseModel):
    current_user: str
    current_database: str
    rolsuper: bool
    rolcreatedb: bool
    rolcreaterole: bool
    rolinherit: bool
    rolreplication: bool
    rolbypassrls: bool


class TemporaryDatabaseDiagnostic(BaseModel):
    runtime: DatabaseIdentity
    migration_configured: bool
    distinct_configuration: bool
    migration: DatabaseIdentity | None


def _identity(connection: Any) -> DatabaseIdentity:
    row = connection.execute(_IDENTITY_QUERY).one()
    return DatabaseIdentity.model_validate(dict(row._mapping))


def _migration_engine():
    return create_engine(
        settings.migration_database_url,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )


@router.get("", response_model=TemporaryDatabaseDiagnostic)
def database_identity(db: Session = Depends(get_db)) -> TemporaryDatabaseDiagnostic:
    migration_configured = bool(settings.migration_database_url)
    distinct_configuration = bool(
        settings.migration_database_url
        and settings.migration_database_url != settings.database_url
    )

    try:
        runtime = _identity(db)
        migration = None
        if migration_configured:
            engine = _migration_engine()
            try:
                with engine.connect() as connection:
                    migration = _identity(connection)
            finally:
                engine.dispose()
    except Exception:
        # Deliberately discard driver details: connection exceptions can include hosts.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database identity diagnostic unavailable",
        ) from None

    return TemporaryDatabaseDiagnostic(
        runtime=runtime,
        migration_configured=migration_configured,
        distinct_configuration=distinct_configuration,
        migration=migration,
    )
