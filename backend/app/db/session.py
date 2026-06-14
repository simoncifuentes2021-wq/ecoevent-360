from collections.abc import Generator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.enums import UserRole

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def set_rls_context(
    db: Session,
    *,
    user_id: UUID,
    role: UserRole | str,
    client_id: UUID | None = None,
) -> None:
    role_value = role.value if isinstance(role, UserRole) else str(role)
    db.execute(text("select set_config('app.current_user_id', :value, false)"), {"value": str(user_id)})
    db.execute(text("select set_config('app.current_role', :value, false)"), {"value": role_value})
    db.execute(
        text("select set_config('app.current_client_id', :value, false)"),
        {"value": str(client_id) if client_id else ""},
    )


def clear_rls_context(db: Session) -> None:
    if not db.is_active:
        return
    db.execute(text("select set_config('app.current_user_id', '', false)"))
    db.execute(text("select set_config('app.current_role', '', false)"))
    db.execute(text("select set_config('app.current_client_id', '', false)"))


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
