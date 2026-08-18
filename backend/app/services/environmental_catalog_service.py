from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.environmental import (
    EcoEquivalenceFactor,
    EnvironmentalFactor,
    EnvironmentalMethodology,
)


def list_factors(db: Session):
    return list(
        db.scalars(
            select(EnvironmentalFactor).order_by(
                EnvironmentalFactor.impact_type, EnvironmentalFactor.technology
            )
        ).all()
    )


def list_methodologies(db: Session):
    return list(
        db.scalars(
            select(EnvironmentalMethodology).order_by(
                EnvironmentalMethodology.action_type, EnvironmentalMethodology.name
            )
        ).all()
    )


def list_equivalences(db: Session):
    return list(db.scalars(select(EcoEquivalenceFactor).order_by(EcoEquivalenceFactor.name)).all())


def create_factor(db: Session, payload):
    item = EnvironmentalFactor(**payload.model_dump(mode="json"))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_factor(db: Session, item_id: UUID, payload):
    item = db.get(EnvironmentalFactor, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Environmental factor not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def create_methodology(db: Session, payload):
    item = EnvironmentalMethodology(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_methodology(db: Session, item_id: UUID, payload):
    item = db.get(EnvironmentalMethodology, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Environmental methodology not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def create_equivalence(db: Session, payload):
    item = EcoEquivalenceFactor(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_equivalence(db: Session, item_id: UUID, payload):
    item = db.get(EcoEquivalenceFactor, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Environmental equivalence not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item
