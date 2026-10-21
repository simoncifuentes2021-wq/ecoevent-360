from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class PersonInput(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=120)
    rut: str = Field(min_length=8, max_length=16)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=240)
    commune: str | None = Field(default=None, max_length=120)


class EmploymentInput(BaseModel):
    event_id: UUID | None = None
    position: str = Field(min_length=1, max_length=160)
    area: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    remuneration: Decimal | None = Field(default=None, ge=0, le=9999999999)
    workplace: str | None = Field(default=None, max_length=240)
    duties: str | None = Field(default=None, max_length=2000)


class PersonCreate(PersonInput):
    client_id: UUID | None = None
    employment: EmploymentInput | None = None


class PersonUpdate(PersonInput):
    """Update reusable identity data without changing faena assignments."""


class EmploymentUpdate(BaseModel):
    """Update one assignment while preserving its person, client, and event."""

    position: str = Field(min_length=1, max_length=160)
    area: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    remuneration: Decimal | None = Field(default=None, ge=0, le=9999999999)
    workplace: str | None = Field(default=None, max_length=240)
    duties: str | None = Field(default=None, max_length=2000)


class PersonImportRow(PersonInput):
    position: str = Field(min_length=1, max_length=160)
    area: str | None = Field(default=None, max_length=120)
    workplace: str | None = Field(default=None, max_length=240)
    start_date: date | None = None
    end_date: date | None = None
    remuneration: Decimal | None = Field(default=None, ge=0, le=9999999999)
    duties: str | None = Field(default=None, max_length=2000)


class PersonImportCommit(BaseModel):
    client_id: UUID | None = None
    event_id: UUID | None = None
    rows: list[PersonImportRow] = Field(min_length=1, max_length=500)


class ExistingPersonAssignmentInput(BaseModel):
    person_id: UUID
    position: str = Field(min_length=1, max_length=160)
    area: str | None = Field(default=None, max_length=120)
    workplace: str | None = Field(default=None, max_length=240)
    start_date: date | None = None
    end_date: date | None = None
    remuneration: Decimal | None = Field(default=None, ge=0, le=9999999999)
    duties: str | None = Field(default=None, max_length=2000)


class ExistingPeopleAssignmentCommit(BaseModel):
    source_event_id: UUID
    target_event_id: UUID
    generate_documents: bool = False
    assignments: list[ExistingPersonAssignmentInput] = Field(min_length=1, max_length=500)


class GenerateMissingDraftsCommit(BaseModel):
    event_id: UUID
    person_ids: list[UUID] = Field(min_length=1, max_length=500)


class PaperBatchPrintRequest(BaseModel):
    person_ids: list[UUID] = Field(min_length=1, max_length=200)
    kinds: list[str] = Field(min_length=1, max_length=2)

    @field_validator("kinds")
    @classmethod
    def validate_kinds(cls, value: list[str]) -> list[str]:
        allowed = {"CONTRACT", "EPP"}
        if len(set(value)) != len(value) or any(kind not in allowed for kind in value):
            raise ValueError("Selecciona contrato, EPP o ambos, sin repetir.")
        return value


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    first_name: str
    last_name: str
    rut: str
    email: str | None
    phone: str | None
    address: str | None
    commune: str | None
    updated_at: datetime
    latest_employment: dict | None = None


class EppItemInput(BaseModel):
    item_code: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=100)
    received_at: date | None = None
    returned_at: date | None = None
    received_conformity: bool = False


class EppInput(BaseModel):
    riohs_received: bool = False
    eirl_completed: bool = False
    delivery_date: date | None = None
    items: list[EppItemInput] = Field(default_factory=list, max_length=40)


class DocumentCreate(BaseModel):
    person_id: UUID
    employment_id: UUID | None = None
    event_id: UUID | None = None
    kind: str = Field(pattern="^(CONTRACT|EPP)$")
    title: str = Field(min_length=2, max_length=180)
    data: dict = Field(default_factory=dict)
    epp: EppInput | None = None


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    data: dict | None = None
    epp: EppInput | None = None


class DocumentContractDefaults(BaseModel):
    employer_name: str = Field(default="", max_length=180)
    employer_rut: str = Field(default="", max_length=16)
    representative_name: str = Field(default="", max_length=180)
    representative_rut: str = Field(default="", max_length=16)
    employer_address: str = Field(default="", max_length=240)
    employer_commune: str = Field(default="Santiago", max_length=120)


class EventEppTemplateItem(BaseModel):
    item_code: str = Field(min_length=1, max_length=40, pattern="^[A-Z0-9_-]+$")
    label: str = Field(min_length=1, max_length=100)


class EventEppTemplateUpdate(BaseModel):
    items: list[EventEppTemplateItem] = Field(min_length=1, max_length=40)


class DocumentRead(BaseModel):
    id: UUID
    person_id: UUID
    person_name: str
    person_rut: str
    employment_id: UUID | None
    event_id: UUID | None
    kind: str
    status: str
    title: str
    data: dict
    epp: dict | None = None
    version: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    can_edit: bool
    has_original_pdf: bool
    has_signed_pdf: bool


class PublicDocumentOpen(BaseModel):
    token: str = Field(min_length=40, max_length=200)
    rut: str = Field(min_length=8, max_length=16)


class PublicDocumentPreview(PublicDocumentOpen):
    pass


class EppWorkerAcknowledgement(BaseModel):
    riohs_received: bool = False
    eirl_completed: bool = False
    items_reviewed: bool = False
    received_item_codes: list[str] = Field(default_factory=list, max_length=40)


class PublicDocumentSign(PublicDocumentOpen):
    worker_name: str = Field(min_length=3, max_length=180)
    worker_signature_data_url: str = Field(min_length=100, max_length=120_000)
    accepted: bool
    electronic_consent: bool
    epp_acknowledgments: EppWorkerAcknowledgement | None = None


class RepresentativeSignatureSave(BaseModel):
    signature_data_url: str = Field(min_length=100, max_length=120_000)


class DocumentSendTogether(BaseModel):
    contract_document_id: UUID
    epp_document_id: UUID


class DocumentBatchSendPair(BaseModel):
    contract_document_id: UUID
    epp_document_id: UUID


class DocumentBatchSendCreate(BaseModel):
    batch_id: UUID
    event_id: UUID
    pairs: list[DocumentBatchSendPair] = Field(min_length=1, max_length=500)


class DocumentBatchRetry(BaseModel):
    item_ids: list[UUID] = Field(min_length=1, max_length=500)


class SignatureLinkRead(BaseModel):
    url: str
    expires_at: datetime
    qr_data_url: str
    signature_notice: str


class ImportValidationError(BaseModel):
    row: int
    field: str
    message: str


class ImportPreview(BaseModel):
    valid_rows: list[dict]
    errors: list[ImportValidationError]
    total_rows: int
    valid_count: int
    error_count: int


class DocumentSummary(BaseModel):
    people: int
    documents: int
    pending: int
    completed: int
    incomplete_epp: int
