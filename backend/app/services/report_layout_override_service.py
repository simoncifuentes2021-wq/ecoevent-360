"""Visual-only overrides layered on the canonical AUTO report renderer."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.core import Report, ReportLayoutOverride, User
from app.models.enums import ReportCompositionMode
from app.schemas.report_schema import ReportLayoutOverrideBatch, ReportLayoutOverrideUpsert
from app.services.report_service import _ensure_admin, ensure_can_access_report


def _report(db: Session, report_id: UUID, user: User) -> Report:
    _ensure_admin(user)
    report = ensure_can_access_report(db, user, report_id)
    if report.composition_mode != ReportCompositionMode.AUTO:
        raise HTTPException(409, "Layout overrides require the original AUTO renderer")
    return report


def list_all(db: Session, report_id: UUID, user: User) -> list[ReportLayoutOverride]:
    _report(db, report_id, user)
    return list(
        db.scalars(
            select(ReportLayoutOverride)
            .where(ReportLayoutOverride.report_id == report_id)
            .order_by(ReportLayoutOverride.element_key)
        )
    )


def upsert(
    db: Session,
    report_id: UUID,
    payload: ReportLayoutOverrideUpsert,
    user: User,
) -> ReportLayoutOverride:
    report = _report(db, report_id, user)
    item = db.scalar(
        select(ReportLayoutOverride).where(
            ReportLayoutOverride.report_id == report_id,
            ReportLayoutOverride.element_key == payload.element_key,
        )
    )
    values = payload.model_dump()
    if item is None:
        item = ReportLayoutOverride(report_id=report_id, **values)
        db.add(item)
    else:
        for key, value in values.items():
            setattr(item, key, value)
        item.updated_at = datetime.utcnow()
    report.edit_version += 1
    db.commit()
    db.refresh(item)
    return item


def batch_upsert(
    db: Session,
    report_id: UUID,
    payload: ReportLayoutOverrideBatch,
    user: User,
) -> list[ReportLayoutOverride]:
    report = _report(db, report_id, user)
    keys = [item.element_key for item in payload.overrides]
    if len(keys) != len(set(keys)):
        raise HTTPException(422, "Duplicate element_key in batch")
    existing = {
        item.element_key: item
        for item in db.scalars(
            select(ReportLayoutOverride).where(
                ReportLayoutOverride.report_id == report_id,
                ReportLayoutOverride.element_key.in_(keys),
            )
        )
    }
    result = []
    for payload_item in payload.overrides:
        values = payload_item.model_dump()
        item = existing.get(payload_item.element_key)
        if item is None:
            item = ReportLayoutOverride(report_id=report_id, **values)
            db.add(item)
        else:
            for key, value in values.items():
                setattr(item, key, value)
            item.updated_at = datetime.utcnow()
        result.append(item)
    report.edit_version += 1
    db.commit()
    return sorted(result, key=lambda item: item.element_key)


def reset_element(db: Session, report_id: UUID, element_key: str, user: User) -> None:
    report = _report(db, report_id, user)
    item = db.scalar(
        select(ReportLayoutOverride).where(
            ReportLayoutOverride.report_id == report_id,
            ReportLayoutOverride.element_key == element_key,
        )
    )
    if item is None:
        raise HTTPException(404, "Layout override not found")
    db.delete(item)
    report.edit_version += 1
    db.commit()


def reset_all(db: Session, report_id: UUID, user: User) -> None:
    report = _report(db, report_id, user)
    result = db.execute(
        delete(ReportLayoutOverride).where(ReportLayoutOverride.report_id == report_id)
    )
    if result.rowcount:
        report.edit_version += 1
    db.commit()
