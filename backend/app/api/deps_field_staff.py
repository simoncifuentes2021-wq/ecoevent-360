from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db, set_field_staff_context
from app.models.core import Event
from app.models.volunteers import FieldStaff


def get_current_field_staff(
    token: str | None = Header(default=None, alias="X-Field-Staff-Token"),
    db: Session = Depends(get_db),
) -> FieldStaff:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="La sesión de terreno venció. Ingresa nuevamente.",
    )
    if not token:
        raise unauthorized
    try:
        claims = decode_access_token(token)
        if claims.get("token_type") != "field_staff":
            raise ValueError("wrong token type")
        staff_id = UUID(str(claims["sub"]))
        event_id = UUID(str(claims["event_id"]))
    except (KeyError, TypeError, ValueError):
        raise unauthorized
    set_field_staff_context(db, field_staff_id=staff_id, event_id=event_id)
    staff = db.get(FieldStaff, staff_id)
    if staff is None or not staff.active or staff.event_id != event_id:
        raise unauthorized
    event = db.get(Event, event_id)
    if event is None:
        raise unauthorized
    if not event.field_staff_portal_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El acceso al formulario de terreno fue desactivado por administración.",
        )
    return staff


def get_ready_field_staff(staff: FieldStaff = Depends(get_current_field_staff)) -> FieldStaff:
    if staff.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cambia la contraseña temporal para continuar.",
        )
    return staff
