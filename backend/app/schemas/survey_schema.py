from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import SurveyStatus


class SurveyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    google_form_url: str | None = None
    google_sheet_url: str | None = None
    status: SurveyStatus | None = None
    opens_at: datetime | None = None
    closes_at: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "SurveyCreate":
        if self.opens_at and self.closes_at and self.opens_at >= self.closes_at:
            raise ValueError("opens_at must be before closes_at")
        return self


class SurveyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    google_form_url: str | None = None
    google_sheet_url: str | None = None
    status: SurveyStatus | None = None
    opens_at: datetime | None = None
    closes_at: datetime | None = None


class SurveyStatusUpdate(BaseModel):
    status: SurveyStatus


class SurveyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    title: str
    description: str | None = None
    google_form_url: str | None = None
    google_sheet_url: str | None = None
    status: SurveyStatus
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SurveyListResponse(BaseModel):
    items: list[SurveyRead]
    total: int
    page: int
    limit: int


class SurveyImportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    survey_id: UUID
    file_url: str | None = None
    imported_rows: int | None = None
    imported_by: UUID | None = None
    imported_at: datetime


class SurveyResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    survey_id: UUID
    event_id: UUID
    zone_id: UUID | None = None
    response_external_id: str | None = None
    response_date: datetime | None = None
    age_range: str | None = None
    origin_commune: str | None = None
    transport_mode: str | None = None
    cleanliness_rating: Decimal | None = None
    bathroom_rating: Decimal | None = None
    recycling_visibility: str | None = None
    separated_waste: bool | None = None
    general_rating: Decimal | None = None
    would_recommend: bool | None = None
    main_problem: str | None = None
    comments: str | None = None
    raw_data: dict | None = None
    created_at: datetime


class SurveyResponseListResponse(BaseModel):
    items: list[SurveyResponseRead]
    total: int
    page: int
    limit: int


class SurveySummaryRead(BaseModel):
    survey_id: UUID
    event_id: UUID
    responses_total: int
    avg_cleanliness_rating: Decimal | None = None
    avg_bathroom_rating: Decimal | None = None
    avg_general_rating: Decimal | None = None
    separated_waste_percentage: Decimal | None = None
    would_recommend_percentage: Decimal | None = None
