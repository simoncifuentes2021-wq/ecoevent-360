from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.services.crud import CRUDService


def crud_router(
    *,
    prefix: str,
    tag: str,
    service: CRUDService[Any, Any],
    create_schema: type[BaseModel],
    read_schema: type[BaseModel],
    update_schema: type[BaseModel] | None = None,
    admin_only: bool = False,
) -> APIRouter:
    write_roles = (UserRole.ADMIN,) if admin_only else (UserRole.ADMIN, UserRole.WORKER)
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("/", response_model=list[read_schema])  # type: ignore[valid-type]
    def list_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
        return service.list(db, skip=skip, limit=limit)

    @router.get("/{item_id}", response_model=read_schema)  # type: ignore[valid-type]
    def get_item(item_id: UUID, db: Session = Depends(get_db)):
        item = service.get(db, item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return item

    @router.post(
        "/",
        response_model=read_schema,  # type: ignore[arg-type]
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_roles(*write_roles))],
    )
    def create_item(payload: create_schema, db: Session = Depends(get_db)):  # type: ignore[valid-type]
        return service.create(db, payload)

    if update_schema:

        @router.patch(
            "/{item_id}",
            response_model=read_schema,  # type: ignore[arg-type]
            dependencies=[Depends(require_roles(*write_roles))],
        )
        def update_item(
            item_id: UUID,
            payload: update_schema,  # type: ignore[valid-type]
            db: Session = Depends(get_db),
        ):
            item = service.get(db, item_id)
            if not item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
            return service.update(db, item, payload)

    @router.delete(
        "/{item_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(require_roles(*write_roles))],
    )
    def delete_item(item_id: UUID, db: Session = Depends(get_db)):
        item = service.get(db, item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        service.delete(db, item)

    return router
