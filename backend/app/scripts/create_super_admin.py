from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.core import User
from app.models.enums import UserRole


def create_super_admin() -> User:
    db = SessionLocal()
    try:
        existing_user = db.scalar(
            select(User).where(User.email == settings.first_super_admin_email)
        )
        if existing_user:
            print(f"SUPER_ADMIN already exists: {existing_user.email} ({existing_user.id})")
            return existing_user

        user = User(
            full_name=settings.first_super_admin_name,
            email=settings.first_super_admin_email,
            password_hash=hash_password(settings.first_super_admin_password),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"SUPER_ADMIN created: {user.email} ({user.id})")
        return user
    finally:
        db.close()


if __name__ == "__main__":
    create_super_admin()

