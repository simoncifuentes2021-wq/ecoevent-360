from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.session import set_rls_context
from app.models.core import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None

    set_rls_context(db, user_id=user.id, role=user.role, client_id=user.client_id)
    db.execute(
        text("update users set last_login_at = :last_login_at where id = :user_id"),
        {
            "last_login_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "user_id": user.id,
        },
    )
    db.commit()
    return user


def issue_token(user: User) -> str:
    return create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "client_id": str(user.client_id) if user.client_id else None,
        }
    )
