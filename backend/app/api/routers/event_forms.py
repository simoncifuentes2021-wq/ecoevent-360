from uuid import UUID
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.event_form_schema import (
    BikeZoneRecordRead,
    EventFormCreate,
    EventFormListResponse,
    EventFormPublicRead,
    EventFormRead,
    EventFormSummaryRead,
    EventFormUpdate,
    EventSessionCreate,
    EventSessionRead,
    EventSessionUpdate,
    FormFieldCreate,
    FormFieldRead,
    FormFieldUpdate,
    FormQRCodeCreate,
    FormQRCodeRead,
    FormResponseCreate,
    FormResponsePublicResult,
    FormResponseRead,
)
from app.services import bike_zone_service, event_form_service, event_session_service, form_qr_service

router = APIRouter(tags=["event forms"])
public_router = APIRouter(prefix="/public/forms", tags=["public forms"])
bike_router = APIRouter(prefix="/bike-zone", tags=["bike zone"])


@router.post("/events/{event_id}/sessions", response_model=EventSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(event_id: UUID, payload: EventSessionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_session_service.create_session(db, event_id, payload, current_user)


@router.get("/events/{event_id}/sessions", response_model=list[EventSessionRead])
def list_sessions(event_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_session_service.list_event_sessions(db, event_id, current_user)


@router.get("/event-sessions/{session_id}", response_model=EventSessionRead)
def get_session(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_session_service.get_session(db, session_id, current_user)


@router.patch("/event-sessions/{session_id}", response_model=EventSessionRead)
def update_session(session_id: UUID, payload: EventSessionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_session_service.update_session(db, session_id, payload, current_user)


@router.delete("/event-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    event_session_service.delete_session(db, session_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/events/{event_id}/forms", response_model=EventFormRead, status_code=status.HTTP_201_CREATED)
def create_form(event_id: UUID, payload: EventFormCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.create_form(db, event_id, payload, current_user)


@router.get("/events/{event_id}/forms", response_model=EventFormListResponse)
def list_forms(
    event_id: UUID,
    session_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = event_form_service.list_event_forms(db, event_id, current_user, session_id, page, limit)
    return EventFormListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/forms/{form_id}", response_model=EventFormRead)
def get_form(form_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.get_form(db, form_id, current_user)


@router.patch("/forms/{form_id}", response_model=EventFormRead)
def update_form(form_id: UUID, payload: EventFormUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.update_form(db, form_id, payload, current_user)


@router.patch("/forms/{form_id}/publish", response_model=EventFormRead)
def publish_form(form_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.publish_form(db, form_id, current_user)


@router.patch("/forms/{form_id}/close", response_model=EventFormRead)
def close_form(form_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.close_form(db, form_id, current_user)


@router.delete("/forms/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_form(form_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    event_form_service.archive_form(db, form_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/forms/{form_id}/fields", response_model=FormFieldRead, status_code=status.HTTP_201_CREATED)
def add_field(form_id: UUID, payload: FormFieldCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.add_field(db, form_id, payload, current_user)


@router.get("/forms/{form_id}/fields", response_model=list[FormFieldRead])
def list_fields(form_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.list_fields(db, form_id, current_user)


@router.patch("/forms/{form_id}/fields/{field_id}", response_model=FormFieldRead)
def update_field(form_id: UUID, field_id: UUID, payload: FormFieldUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.update_field(db, form_id, field_id, payload, current_user)


@router.delete("/forms/{form_id}/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(form_id: UUID, field_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    event_form_service.delete_field(db, form_id, field_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/forms/{form_id}/fields/reorder", response_model=list[FormFieldRead])
def reorder_fields(form_id: UUID, field_ids: list[UUID], db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.reorder_fields(db, form_id, field_ids, current_user)


@router.get("/forms/{form_id}/responses", response_model=list[FormResponseRead])
def list_responses(form_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.list_responses(db, form_id, current_user)


@router.get("/forms/{form_id}/responses/{response_id}", response_model=FormResponseRead)
def get_response(form_id: UUID, response_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.get_response(db, form_id, response_id, current_user)


@router.get("/forms/{form_id}/summary", response_model=EventFormSummaryRead)
def get_summary(form_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return event_form_service.summary(db, form_id, current_user)


@router.get("/forms/{form_id}/export-csv")
def export_csv(form_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    content = event_form_service.export_csv(db, form_id, current_user)
    return PlainTextResponse(content, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="form-{form_id}.csv"'})


@router.post("/forms/{form_id}/qr", response_model=FormQRCodeRead, status_code=status.HTTP_201_CREATED)
def create_form_qr(
    form_id: UUID,
    payload: FormQRCodeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return form_qr_service.create_form_qr(db, form_id, payload, current_user, public_base_url=_request_public_base_url(request))


@router.get("/forms/{form_id}/qr", response_model=list[FormQRCodeRead])
def list_form_qr_codes(
    form_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return form_qr_service.list_form_qr_codes(db, form_id, current_user, public_base_url=_request_public_base_url(request))


@router.get("/form-qr/{qr_id}/download")
def download_form_qr(qr_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    content, content_type, filename = form_qr_service.get_download_content(db, qr_id, current_user)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/form-qr/{qr_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form_qr(qr_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    form_qr_service.delete_qr(db, qr_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@public_router.get("/{slug}", response_model=EventFormPublicRead)
def get_public_form(slug: str, lang: str | None = None, db: Session = Depends(get_db)):
    form = event_form_service.get_public_form_or_404(db, slug)
    return event_form_service.public_form_payload(form, lang)


@public_router.post("/{slug}/submit", response_model=FormResponsePublicResult, status_code=status.HTTP_201_CREATED)
def submit_public_form(slug: str, payload: FormResponseCreate, db: Session = Depends(get_db)):
    response, bike_code = event_form_service.submit_public_form(db, slug, payload)
    return FormResponsePublicResult(response_code=response.response_code, bike_zone_code=bike_code, message="Respuesta recibida correctamente.")


@bike_router.get("/verify/{code}", response_model=BikeZoneRecordRead)
def verify_bike_code(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return bike_zone_service.verify(db, code, current_user)


@bike_router.patch("/verify/{code}/check-in", response_model=BikeZoneRecordRead)
def check_in_bike(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return bike_zone_service.check_in(db, code, current_user)


@bike_router.patch("/verify/{code}/check-out", response_model=BikeZoneRecordRead)
def check_out_bike(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return bike_zone_service.check_out(db, code, current_user)


@bike_router.post("/{code}/qr", response_model=FormQRCodeRead, status_code=status.HTTP_201_CREATED)
def create_bike_zone_qr(
    code: str,
    request: Request,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return form_qr_service.create_bike_zone_qr(
        db,
        code,
        current_user,
        force=force,
        public_base_url=_request_public_base_url(request),
    )


def _request_public_base_url(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if origin and _is_public_http_origin(origin):
        return origin
    referer = request.headers.get("referer")
    if not referer:
        return None
    parsed = urlparse(referer)
    if parsed.scheme in {"http", "https"} and parsed.netloc and parsed.hostname not in {"localhost", "127.0.0.1"}:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def _is_public_http_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and parsed.hostname not in {"localhost", "127.0.0.1"}
