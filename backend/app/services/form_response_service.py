from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core import User
from app.schemas.event_form_schema import FormResponseCreate
from app.services import event_form_service


def submit_public_form(db: Session, slug: str, payload: FormResponseCreate):
    return event_form_service.submit_public_form(db, slug, payload)


def list_responses(db: Session, form_id: UUID, user: User):
    return event_form_service.list_responses(db, form_id, user)


def get_response(db: Session, form_id: UUID, response_id: UUID, user: User):
    return event_form_service.get_response(db, form_id, response_id, user)


def summary(db: Session, form_id: UUID, user: User):
    return event_form_service.summary(db, form_id, user)


def export_csv(db: Session, form_id: UUID, user: User):
    return event_form_service.export_csv(db, form_id, user)
