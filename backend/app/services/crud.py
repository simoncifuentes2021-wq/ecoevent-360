from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)
CreateT = TypeVar("CreateT", bound=BaseModel)


class CRUDService(Generic[ModelT, CreateT]):
    def __init__(self, model: type[ModelT]):
        self.model = model

    def list(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[ModelT]:
        return list(db.scalars(select(self.model).offset(skip).limit(limit)).all())

    def get(self, db: Session, item_id: int) -> ModelT | None:
        return db.get(self.model, item_id)

    def create(self, db: Session, payload: CreateT | dict[str, Any]) -> ModelT:
        data = payload.model_dump() if isinstance(payload, BaseModel) else payload
        item = self.model(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update(self, db: Session, item: ModelT, payload: BaseModel | dict[str, Any]) -> ModelT:
        data = payload.model_dump(exclude_unset=True) if isinstance(payload, BaseModel) else payload
        for key, value in data.items():
            setattr(item, key, value)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, item: ModelT) -> None:
        db.delete(item)
        db.commit()

