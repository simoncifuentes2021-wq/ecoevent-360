from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import can_manage_event
from app.models.core import BikeZoneRecord, FormResponse, User
from app.models.enums import BikeZoneStatus, UserRole


def get_record_by_code(db: Session, code: str) -> BikeZoneRecord:
    normalized = code.strip().upper()
    record = db.scalar(select(BikeZoneRecord).where(BikeZoneRecord.code == normalized))
    if not record:
        record = db.scalar(
            select(BikeZoneRecord)
            .join(FormResponse, FormResponse.id == BikeZoneRecord.response_id)
            .where(FormResponse.response_code == normalized)
        )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bike Zone code not found")
    return record


def _ensure_can_operate(db: Session, record: BikeZoneRecord, user: User) -> None:
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.LOGISTICS_OPERATOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if user.role == UserRole.LOGISTICS_OPERATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not can_manage_event(user, record.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def verify(db: Session, code: str, user: User) -> BikeZoneRecord:
    record = get_record_by_code(db, code)
    _ensure_can_operate(db, record, user)
    return record


def check_in(db: Session, code: str, user: User) -> BikeZoneRecord:
    record = verify(db, code, user)
    if record.check_in_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bike already checked in")
    record.status = BikeZoneStatus.CHECKED_IN
    record.check_in_at = datetime.utcnow()
    record.checked_in_by = user.id
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


def check_out(db: Session, code: str, user: User) -> BikeZoneRecord:
    record = verify(db, code, user)
    if not record.check_in_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bike must be checked in first")
    if record.check_out_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bike already checked out")
    record.status = BikeZoneStatus.CHECKED_OUT
    record.check_out_at = datetime.utcnow()
    record.checked_out_by = user.id
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record
