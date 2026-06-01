from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.core import Service
from app.schemas.service_schema import ServiceCreate, ServiceUpdate


def get_service_or_404(db: Session, service_id: UUID) -> Service:
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


def create_service(db: Session, payload: ServiceCreate) -> Service:
    service = Service(**payload.model_dump(), is_active=True)
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def list_services(
    db: Session,
    *,
    q: str | None,
    is_active: bool | None,
    page: int,
    limit: int,
) -> tuple[list[Service], int]:
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                Service.name.ilike(pattern),
                Service.category.ilike(pattern),
                Service.description.ilike(pattern),
            )
        )
    if is_active is not None:
        filters.append(Service.is_active == is_active)

    total = db.scalar(select(func.count()).select_from(Service).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Service)
            .where(*filters)
            .order_by(Service.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def update_service(db: Session, service_id: UUID, payload: ServiceUpdate) -> Service:
    service = get_service_or_404(db, service_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def deactivate_service(db: Session, service_id: UUID) -> Service:
    service = get_service_or_404(db, service_id)
    service.is_active = False
    db.add(service)
    db.commit()
    db.refresh(service)
    return service
