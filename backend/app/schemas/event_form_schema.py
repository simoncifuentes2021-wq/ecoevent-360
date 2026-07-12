from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import BikeZoneStatus, EventFormStatus, EventFormType, FormFieldType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EventSessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    session_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    venue_name: str | None = Field(default=None, max_length=180)
    stage_name: str | None = Field(default=None, max_length=180)
    expected_attendees: int = Field(default=0, ge=0)
    real_attendees: int | None = Field(default=None, ge=0)
    status: str = Field(default="PLANNED", max_length=50)

    @field_validator("description", "session_date", "start_time", "end_time", "venue_name", "stage_name", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


class EventSessionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    session_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    venue_name: str | None = Field(default=None, max_length=180)
    stage_name: str | None = Field(default=None, max_length=180)
    expected_attendees: int | None = Field(default=None, ge=0)
    real_attendees: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=50)

    @field_validator("description", "session_date", "start_time", "end_time", "venue_name", "stage_name", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


class EventSessionRead(EventSessionCreate, ORMModel):
    id: UUID
    event_id: UUID
    created_at: datetime
    updated_at: datetime


class FormFieldOptionCreate(BaseModel):
    label: str = Field(min_length=1, max_length=180)
    value: str = Field(min_length=1, max_length=120)
    sort_order: int = 0
    translations: dict[str, str] | None = None


class FormFieldOptionRead(ORMModel):
    id: UUID
    field_id: UUID
    label: str
    value: str
    sort_order: int
    created_at: datetime


class FormFieldTranslationRead(ORMModel):
    language: str
    label: str
    help_text: str | None = None
    placeholder: str | None = None


class FormFieldCreate(BaseModel):
    label: str = Field(min_length=1, max_length=220)
    field_key: str = Field(min_length=1, max_length=120)
    field_type: FormFieldType
    help_text: str | None = None
    placeholder: str | None = Field(default=None, max_length=220)
    is_required: bool = False
    sort_order: int = 0
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    max_length: int | None = Field(default=None, ge=1)
    analytics_key: str | None = Field(default=None, max_length=120)
    is_active: bool = True
    options: list[FormFieldOptionCreate] = []
    translations: dict[str, dict[str, str | None]] | None = None

    @field_validator("field_key", "analytics_key", mode="before")
    @classmethod
    def normalize_key(cls, value):
        if isinstance(value, str):
            return value.strip().lower().replace(" ", "_")
        return value


class FormFieldUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=220)
    field_key: str | None = Field(default=None, min_length=1, max_length=120)
    field_type: FormFieldType | None = None
    help_text: str | None = None
    placeholder: str | None = Field(default=None, max_length=220)
    is_required: bool | None = None
    sort_order: int | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    max_length: int | None = Field(default=None, ge=1)
    analytics_key: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    options: list[FormFieldOptionCreate] | None = None
    translations: dict[str, dict[str, str | None]] | None = None

    @field_validator("field_key", "analytics_key", mode="before")
    @classmethod
    def normalize_key(cls, value):
        if isinstance(value, str):
            return value.strip().lower().replace(" ", "_")
        return value


class FormFieldRead(ORMModel):
    id: UUID
    form_id: UUID
    label: str
    field_key: str
    field_type: FormFieldType
    help_text: str | None = None
    placeholder: str | None = None
    is_required: bool
    sort_order: int
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    max_length: int | None = None
    analytics_key: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    options: list[FormFieldOptionRead] = []


class EventFormCreate(BaseModel):
    session_id: UUID | None = None
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    form_type: EventFormType = EventFormType.CUSTOM
    public_slug: str | None = Field(default=None, max_length=220)
    status: EventFormStatus | None = None
    banner_url: str | None = None
    primary_logo_url: str | None = None
    secondary_logo_url: str | None = None
    primary_color: str = "#16b86a"
    show_event_name: bool = True
    show_session_name: bool = True
    collect_personal_data: bool = False
    default_language: str = "es"
    available_languages: list[str] = ["es"]
    requires_language_selection: bool = False
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    generate_template: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> "EventFormCreate":
        if self.opens_at and self.closes_at and self.opens_at >= self.closes_at:
            raise ValueError("opens_at must be before closes_at")
        if self.default_language not in self.available_languages:
            self.available_languages = [self.default_language, *self.available_languages]
        return self


class EventFormUpdate(BaseModel):
    session_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    form_type: EventFormType | None = None
    public_slug: str | None = Field(default=None, max_length=220)
    status: EventFormStatus | None = None
    banner_url: str | None = None
    primary_logo_url: str | None = None
    secondary_logo_url: str | None = None
    primary_color: str | None = None
    show_event_name: bool | None = None
    show_session_name: bool | None = None
    collect_personal_data: bool | None = None
    default_language: str | None = None
    available_languages: list[str] | None = None
    requires_language_selection: bool | None = None
    opens_at: datetime | None = None
    closes_at: datetime | None = None


class EventFormRead(ORMModel):
    id: UUID
    event_id: UUID
    session_id: UUID | None = None
    title: str
    description: str | None = None
    form_type: EventFormType
    public_slug: str
    status: EventFormStatus
    banner_url: str | None = None
    primary_logo_url: str | None = None
    secondary_logo_url: str | None = None
    primary_color: str
    show_event_name: bool
    show_session_name: bool
    collect_personal_data: bool
    default_language: str
    available_languages: list[str]
    requires_language_selection: bool
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    fields: list[FormFieldRead] = []


class EventFormListResponse(BaseModel):
    items: list[EventFormRead]
    total: int
    page: int
    limit: int


class PublicFormOptionRead(BaseModel):
    label: str
    value: str
    sort_order: int


class PublicFormFieldRead(BaseModel):
    label: str
    field_key: str
    field_type: FormFieldType
    help_text: str | None = None
    placeholder: str | None = None
    is_required: bool
    sort_order: int
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    max_length: int | None = None
    options: list[PublicFormOptionRead] = []


class EventFormPublicRead(BaseModel):
    title: str
    description: str | None = None
    form_type: EventFormType
    public_slug: str
    banner_url: str | None = None
    primary_logo_url: str | None = None
    secondary_logo_url: str | None = None
    primary_color: str
    show_event_name: bool
    show_session_name: bool
    event_name: str | None = None
    session_name: str | None = None
    venue_name: str | None = None
    default_language: str
    available_languages: list[str]
    requires_language_selection: bool
    language: str | None = None
    needs_language_selection: bool = False
    submit_label: str = "Enviar encuesta"
    fields: list[PublicFormFieldRead] = []


class FormResponseCreate(BaseModel):
    language: str = "es"
    answers: dict[str, object]
    metadata: dict | None = None


class FormAnswerRead(ORMModel):
    id: UUID
    field_id: UUID
    value_text: str | None = None
    value_number: Decimal | None = None
    value_boolean: bool | None = None
    value_date: date | None = None
    value_json: dict | list | None = None
    created_at: datetime


class FormResponseRead(ORMModel):
    id: UUID
    form_id: UUID
    event_id: UUID
    session_id: UUID | None = None
    response_code: str | None = None
    respondent_name: str | None = None
    respondent_email: str | None = None
    respondent_phone: str | None = None
    language: str
    raw_data: dict
    submitted_at: datetime
    answers: list[FormAnswerRead] = []


class FormResponsePublicResult(BaseModel):
    response_code: str | None = None
    bike_zone_code: str | None = None
    message: str


class FormQRCodeCreate(BaseModel):
    label: str = Field(min_length=1, max_length=180)
    qr_type: str = Field(default="FORM", max_length=50)
    language: str | None = Field(default=None, max_length=10)
    force: bool = False


class FormQRCodeRead(ORMModel):
    id: UUID
    form_id: UUID
    event_id: UUID
    session_id: UUID | None = None
    label: str
    target_url: str
    qr_type: str
    language: str | None = None
    file_url: str | None = None
    format: str
    created_by: UUID | None = None
    created_at: datetime


class EventFormSummaryRead(BaseModel):
    form_id: UUID
    total_responses: int
    responses_by_session: list[dict]
    responses_by_day: list[dict]
    responses_by_language: list[dict]
    average_rating: float | None = None
    recommendation_rate: float | None = None
    transport_modes: list[dict]
    countries: list[dict]
    regions: list[dict]
    main_problems: list[dict]
    bike_zone_total: int
    bike_zone_checked_in: int
    bike_zone_checked_out: int
    comments_sample: list[str]


class FormsSessionComparisonItem(BaseModel):
    session_id: UUID
    session_name: str
    session_date: date | None = None
    start_time: time | None = None
    total_forms: int = 0
    active_forms: int = 0
    total_responses: int = 0
    transport_modes: list[dict] = Field(default_factory=list)
    average_rating: float | None = None
    recommendation_rate: float | None = None
    main_problems: list[dict] = Field(default_factory=list)
    bike_zone_total: int = 0
    bike_zone_checked_in: int = 0
    bike_zone_checked_out: int = 0


class FormsSessionComparisonResponse(BaseModel):
    event_id: UUID
    sessions: list[FormsSessionComparisonItem]


class BikeZoneRecordRead(ORMModel):
    id: UUID
    response_id: UUID
    event_id: UUID
    session_id: UUID | None = None
    code: str
    status: BikeZoneStatus
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
