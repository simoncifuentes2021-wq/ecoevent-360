from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class VolunteerActivationCreate(BaseModel):
    event_id: UUID
    session_id: UUID | None = None
    name: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=3000)
    location_name: str | None = Field(default=None, max_length=180)
    address: str | None = Field(default=None, max_length=1000)
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))
    starts_at: datetime
    ends_at: datetime | None = None
    responsible_user_id: UUID | None = None
    capacity: int | None = Field(default=None, ge=1, le=1_000_000)
    allowed_material_ids: list[UUID] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.ends_at and self.ends_at < self.starts_at:
            raise ValueError("La fecha de término debe ser posterior al inicio")
        return self


class VolunteerActivationUpdate(BaseModel):
    session_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=3000)
    location_name: str | None = Field(default=None, max_length=180)
    address: str | None = Field(default=None, max_length=1000)
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    responsible_user_id: UUID | None = None
    capacity: int | None = Field(default=None, ge=1, le=1_000_000)
    status: Literal["DRAFT", "ACTIVE", "CLOSED", "CANCELLED", "ARCHIVED"] | None = None
    allowed_material_ids: list[UUID] | None = Field(default=None, max_length=100)


class VolunteerActivationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    session_id: UUID | None
    event_name: str | None = None
    name: str
    description: str | None
    location_name: str | None
    address: str | None
    starts_at: datetime
    ends_at: datetime | None
    responsible_user_id: UUID | None
    status: str
    capacity: int | None
    public_slug: str
    created_at: datetime
    updated_at: datetime
    volunteer_count: int = 0
    contribution_count: int = 0
    total_weight_kg: Decimal = Decimal("0")
    allowed_material_ids: list[UUID] = Field(default_factory=list)


class FieldStaffCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    rut: str = Field(min_length=9, max_length=16)
    activation_ids: list[UUID] = Field(min_length=1, max_length=100)


class FieldStaffUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=180)
    rut: str | None = Field(default=None, min_length=9, max_length=16)
    activation_ids: list[UUID] | None = Field(default=None, max_length=100)
    active: bool | None = None


class FieldStaffPortalUpdate(BaseModel):
    enabled: bool


class FieldStaffRead(BaseModel):
    id: UUID
    event_id: UUID
    full_name: str
    rut: str
    active: bool
    must_change_password: bool
    activation_ids: list[UUID]
    activation_names: list[str]
    created_at: datetime


class FieldStaffCreateRead(BaseModel):
    staff: FieldStaffRead
    temporary_password: str


class FieldStaffLogin(BaseModel):
    event_id: UUID
    rut: str = Field(min_length=9, max_length=16)
    password: str = Field(min_length=1, max_length=128)


class FieldStaffLoginRead(BaseModel):
    access_token: str
    token_type: Literal["field_staff"]
    staff: FieldStaffRead
    event_name: str


class FieldStaffPasswordChange(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)


class FieldStaffVolunteerRegistration(BaseModel):
    volunteer_id: UUID | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=180)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=40)
    organization: str | None = Field(default=None, max_length=180)
    consent_accepted: bool = False
    marketing_consent: bool = False

    @model_validator(mode="after")
    def validate_existing_or_new(self):
        if self.volunteer_id is None:
            if not self.full_name or not self.email or not self.phone:
                raise ValueError("Para crear un voluntario ingresa nombre, correo y teléfono")
            if not self.consent_accepted:
                raise ValueError("El voluntario debe aceptar el registro de sus datos")
        return self


class ContributionItemCreate(BaseModel):
    material_id: UUID
    weight_kg: Decimal = Field(gt=Decimal("0"), le=Decimal("1000000"), max_digits=12, decimal_places=3)


class ContributionCreate(BaseModel):
    volunteer_id: UUID
    items: list[ContributionItemCreate] = Field(min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=80)

    @field_validator("items")
    @classmethod
    def unique_materials(cls, items):
        ids = [item.material_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Agrega cada material una sola vez y ajusta su peso")
        return items


class ContributionUpdate(BaseModel):
    items: list[ContributionItemCreate] = Field(min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("items")
    @classmethod
    def unique_materials(cls, items):
        ids = [item.material_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Agrega cada material una sola vez y ajusta su peso")
        return items


class ContributionVoid(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class ContributionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    material_id: UUID
    material_name_snapshot: str
    unit_snapshot: str
    weight_kg: Decimal


class ContributionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    volunteer_id: UUID
    volunteer_name: str
    volunteer_email: str | None = None
    volunteer_code: str
    activation_id: UUID
    activation_name: str
    event_id: UUID
    event_name: str
    registered_by_user_id: UUID | None
    registered_by_field_staff_id: UUID | None = None
    registered_by_name: str | None = None
    registered_at: datetime
    notes: str | None
    total_weight_kg: Decimal
    status: str
    void_reason: str | None
    voided_at: datetime | None
    email_status: str
    items: list[ContributionItemRead]
    evidence_count: int = 0


class PublicVolunteerRegistration(BaseModel):
    activation_slug: str = Field(min_length=16, max_length=72)
    full_name: str = Field(min_length=2, max_length=180)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=40)
    organization: str | None = Field(default=None, max_length=180)
    consent_accepted: Literal[True]
    marketing_consent: bool = False

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Ingresa tu nombre completo")
        return value


class PublicVolunteerRegistrationRead(BaseModel):
    activation_name: str
    message: str


class VolunteerManualCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=40)
    organization: str | None = Field(default=None, max_length=180)
    consent_accepted: Literal[True]
    marketing_consent: bool = False

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Ingresa el nombre completo")
        return value


class VolunteerResolveRead(BaseModel):
    id: UUID
    full_name: str
    unique_code: str
    already_in_activation: bool
    total_weight_kg_in_event: Decimal


class PublicActivationRead(BaseModel):
    name: str
    description: str | None
    event_name: str
    location_name: str | None
    address: str | None
    starts_at: datetime
    ends_at: datetime | None
    status: str
    consent_text: str
    consent_version: str


class PublicContributionItemRead(BaseModel):
    material: str
    weight_kg: Decimal
    unit: str


class PublicContributionEvidenceRead(BaseModel):
    id: UUID
    description: str | None
    file_type: str | None


class PublicContributionRead(BaseModel):
    id: UUID
    activation: str
    event: str
    registered_at: datetime
    total_weight_kg: Decimal
    items: list[PublicContributionItemRead]
    evidences: list[PublicContributionEvidenceRead]


class PublicVolunteerImpactRead(BaseModel):
    full_name: str
    total_weight_kg: Decimal
    activation_count: int
    contribution_count: int
    material_totals: dict[str, Decimal]
    contributions: list[PublicContributionRead]


class VolunteerListItem(BaseModel):
    id: UUID
    full_name: str
    email: str | None
    phone: str | None
    organization: str | None
    unique_code: str
    status: str
    registered_at: datetime
    activation_count: int
    contribution_count: int
    total_weight_kg: Decimal


class VolunteerListResponse(BaseModel):
    items: list[VolunteerListItem]
    total: int
    page: int
    limit: int


class VolunteerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=180)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    organization: str | None = Field(default=None, max_length=180)
    status: Literal["ACTIVE", "INACTIVE", "ARCHIVED"] | None = None


class VolunteerRead(BaseModel):
    id: UUID
    full_name: str
    email: str | None
    phone: str | None
    organization: str | None
    unique_code: str
    status: str
    consent_accepted_at: datetime | None
    marketing_consent: bool


class VolunteerImpactRead(PublicVolunteerImpactRead):
    email: str
    phone: str | None
    unique_code: str
    first_contribution_at: datetime | None
    last_contribution_at: datetime | None


class VolunteerDashboardRead(BaseModel):
    unique_volunteers: int
    participations: int
    contributions: int
    total_weight_kg: Decimal
    active_activations: int
    average_per_volunteer_kg: Decimal
    by_date: list[dict]
    by_activation: list[dict]
    by_material: list[dict]
    new_volunteers_by_date: list[dict]


class ContributionListRead(BaseModel):
    items: list[ContributionRead]
    total: int
    page: int
    limit: int
