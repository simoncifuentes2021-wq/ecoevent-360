from collections.abc import Generator
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.enums import UserRole

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

_RLS_CONTEXT_KEY = "rls_context"


def _apply_rls_context(connection: Connection, context: dict[str, str]) -> None:
    connection.execute(
        text("select set_config('app.current_user_id', :value, true)"),
        {"value": context["user_id"]},
    )
    connection.execute(
        text("select set_config('app.current_role', :value, true)"),
        {"value": context["role"]},
    )
    connection.execute(
        text("select set_config('app.current_client_id', :value, true)"),
        {"value": context["client_id"]},
    )


@event.listens_for(Session, "after_begin")
def _restore_rls_context(
    session: Session,
    _transaction: object,
    connection: Connection,
) -> None:
    context = session.info.get(_RLS_CONTEXT_KEY)
    if context:
        _apply_rls_context(connection, context)


def set_rls_context(
    db: Session,
    *,
    user_id: UUID,
    role: UserRole | str,
    client_id: UUID | None = None,
) -> None:
    role_value = role.value if isinstance(role, UserRole) else str(role)
    context = {
        "user_id": str(user_id),
        "role": role_value,
        "client_id": str(client_id) if client_id else "",
    }
    db.info[_RLS_CONTEXT_KEY] = context
    _apply_rls_context(db.connection(), context)


def clear_rls_context(db: Session) -> None:
    if db.is_active:
        db.rollback()
    db.info.pop(_RLS_CONTEXT_KEY, None)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            clear_rls_context(db)
        except Exception:
            db.rollback()
        db.close()
