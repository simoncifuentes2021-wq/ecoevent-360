from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.domain import DashboardSummary
from app.services.domain import event_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/events/{event_id}", response_model=DashboardSummary)
def get_event_dashboard(event_id: int, db: Session = Depends(get_db)):
    return event_dashboard(db, event_id)

