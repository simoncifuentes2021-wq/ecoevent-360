from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.core import Client, Event
from app.schemas.client_schema import ClientCreate, ClientUpdate


def get_client_or_404(db: Session, client_id: UUID) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


def create_client(db: Session, payload: ClientCreate) -> Client:
    client = Client(**payload.model_dump(), is_active=True)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def list_clients(
    db: Session,
    *,
    q: str | None,
    is_active: bool | None,
    page: int,
    limit: int,
) -> tuple[list[Client], int]:
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                Client.business_name.ilike(pattern),
                Client.rut.ilike(pattern),
                Client.contact_email.ilike(pattern),
                Client.contact_name.ilike(pattern),
            )
        )
    if is_active is not None:
        filters.append(Client.is_active == is_active)

    base = select(Client).where(*filters)
    total = db.scalar(select(func.count()).select_from(Client).where(*filters)) or 0
    items = list(
        db.scalars(
            base.order_by(Client.created_at.desc()).offset((page - 1) * limit).limit(limit)
        ).all()
    )
    return items, total


def update_client(db: Session, client_id: UUID, payload: ClientUpdate) -> Client:
    client = get_client_or_404(db, client_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    client.updated_at = datetime.utcnow()
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def deactivate_client(db: Session, client_id: UUID) -> Client:
    client = get_client_or_404(db, client_id)
    client.is_active = False
    client.updated_at = datetime.utcnow()
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def list_client_events(
    db: Session,
    *,
    client_id: UUID,
    page: int,
    limit: int,
) -> tuple[list[Event], int]:
    filters = [Event.client_id == client_id]
    base = select(Event).where(*filters)
    total = db.scalar(select(func.count()).select_from(Event).where(*filters)) or 0
    items = list(
        db.scalars(
            base.order_by(Event.start_date.desc()).offset((page - 1) * limit).limit(limit)
        ).all()
    )
    return items, total

