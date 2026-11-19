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
_FIELD_STAFF_CONTEXT_KEY = "field_staff_rls_context"


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
    field_context = session.info.get(_FIELD_STAFF_CONTEXT_KEY)
    if field_context:
        for key, value in field_context.items():
            connection.execute(text("select set_config(:key, :value, true)"), {"key": key, "value": value})


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


def set_public_form_rls_context(
    db: Session,
    *,
    form_id: UUID,
    response_id: UUID | None = None,
    idempotency_key: str | None = None,
) -> None:
    """Authorize the current public form and, optionally, its submission."""
    connection = db.connection()
    connection.execute(
        text("select set_config('app.public_form_id', :value, true)"),
        {"value": str(form_id)},
    )
    connection.execute(
        text("select set_config('app.public_response_id', :value, true)"),
        {"value": str(response_id) if response_id else ""},
    )
    connection.execute(
        text("select set_config('app.public_idempotency_key', :value, true)"),
        {"value": idempotency_key or ""},
    )


def set_public_waste_context(db: Session, token: str) -> None:
    db.connection().execute(
        text("select set_config('app.public_waste_token', :value, true)"),
        {"value": token},
    )


def set_public_document_context(db: Session, token_hash: str) -> None:
    """Scope RLS to one unexpired document signing capability."""
    db.connection().execute(
        text("select set_config('app.public_document_token_hash', :value, true)"),
        {"value": token_hash},
    )


def set_public_volunteer_context(
    db: Session,
    *,
    activation_slug: str | None = None,
    email_hash: str | None = None,
    token_hash: str | None = None,
    volunteer_code: str | None = None,
    phone_normalized: str | None = None,
) -> None:
    """Restrict public volunteer queries to one registration or history capability."""
    connection = db.connection()
    for key, value in (
        ("app.public_volunteer_slug", activation_slug),
        ("app.public_volunteer_email_hash", email_hash),
        ("app.public_volunteer_token_hash", token_hash),
        ("app.public_volunteer_code", volunteer_code),
        ("app.public_volunteer_phone", phone_normalized),
    ):
        connection.execute(
            text("select set_config(:key, :value, true)"),
            {"key": key, "value": value or ""},
        )


def set_field_staff_context(
    db: Session,
    *,
    field_staff_id: UUID | None = None,
    event_id: UUID | None = None,
    rut_normalized: str | None = None,
    activation_id: UUID | None = None,
) -> None:
    """Set transaction-local scope for an independently authenticated field operator."""
    values = (
        ("app.field_staff_id", str(field_staff_id) if field_staff_id else ""),
        ("app.field_staff_event_id", str(event_id) if event_id else ""),
        ("app.field_staff_rut", rut_normalized or ""),
        ("app.field_staff_activation_id", str(activation_id) if activation_id else ""),
    )
    context = {key: value for key, value in values}
    db.info[_FIELD_STAFF_CONTEXT_KEY] = context
    connection = db.connection()
    for key, value in values:
        connection.execute(
            text("select set_config(:key, :value, true)"),
            {"key": key, "value": value},
        )


def set_document_event_context(db: Session, event_id: UUID) -> None:
    """Limit supervisor person writes to the client of one authorized event."""
    db.connection().execute(
        text("select set_config('app.document_event_id', :value, true)"),
        {"value": str(event_id)},
    )


def clear_rls_context(db: Session) -> None:
    if db.is_active:
        db.rollback()
    db.info.pop(_RLS_CONTEXT_KEY, None)
    db.info.pop(_FIELD_STAFF_CONTEXT_KEY, None)


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
