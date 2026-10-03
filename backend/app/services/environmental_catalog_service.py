from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.core import WasteType
from app.models.environmental import (
    EcoEquivalenceFactor,
    EnvironmentalFactor,
    EnvironmentalMethodology,
    WasteCollectionEquivalenceFactor,
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


def list_waste_collection_equivalences(db: Session):
    items = db.scalars(
        select(WasteCollectionEquivalenceFactor)
        .options(selectinload(WasteCollectionEquivalenceFactor.waste_type))
        .order_by(WasteCollectionEquivalenceFactor.kind, WasteCollectionEquivalenceFactor.name)
    ).all()
    return [
        {
            **{column.name: getattr(item, column.name) for column in item.__table__.columns},
            "waste_type_name": item.waste_type.name if item.waste_type else None,
        }
        for item in items
    ]


def create_waste_collection_equivalence(db: Session, payload):
    if db.scalar(
        select(WasteCollectionEquivalenceFactor.id).where(
            WasteCollectionEquivalenceFactor.key == payload.key
        )
    ):
        raise HTTPException(status_code=409, detail="Ya existe una equivalencia con esa clave")
    if payload.waste_type_id and db.get(WasteType, payload.waste_type_id) is None:
        raise HTTPException(status_code=404, detail="El material indicado no existe")
    data = payload.model_dump()
    data["source_url"] = str(payload.source_url) if payload.source_url else None
    item = WasteCollectionEquivalenceFactor(**data)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una equivalencia con esa clave") from exc
    db.refresh(item)
    return next(row for row in list_waste_collection_equivalences(db) if row["id"] == item.id)


def update_waste_collection_equivalence(db: Session, item_id: UUID, payload):
    item = db.get(WasteCollectionEquivalenceFactor, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Equivalencia de Acopios no encontrada")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "source_url":
            value = str(value) if value else None
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return next(row for row in list_waste_collection_equivalences(db) if row["id"] == item_id)


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
