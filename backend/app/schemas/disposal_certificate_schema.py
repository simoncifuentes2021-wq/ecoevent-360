from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DisposalCertificateMaterialInput(BaseModel):
    waste_type_id: UUID
    final_weight_kg: Decimal = Field(gt=0, le=1000000, max_digits=12, decimal_places=3)


class DisposalCertificateCreate(BaseModel):
    materials: list[DisposalCertificateMaterialInput] = Field(min_length=1, max_length=100)
    recipient_name: str | None = Field(default=None, max_length=240)
    recipient_rut: str | None = Field(default=None, max_length=30)
    event_name: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def unique_materials(self):
        ids = [item.waste_type_id for item in self.materials]
        if len(ids) != len(set(ids)):
            raise ValueError("No repitas el mismo material en el certificado")
        return self


class DisposalCertificateMaterialContext(BaseModel):
    waste_type_id: UUID
    name: str
    received_kg: Decimal


class DisposalCertificateListItem(BaseModel):
    id: UUID
    certificate_number: str
    certificate_date: date
    total_kg: Decimal
    recipient_name: str
    receiving_facility_name: str
    sha256: str
    generated_at: datetime


class DisposalCertificateContext(BaseModel):
    event_id: UUID
    event_name: str
    recipient_name: str
    recipient_rut: str | None
    materials: list[DisposalCertificateMaterialContext]
    certificates: list[DisposalCertificateListItem]


class DisposalCertificateDefaultsUpdate(BaseModel):
    issuer_name: str = Field(default="", max_length=180)
    issuer_rut: str = Field(default="", max_length=30)
    issuer_address: str = Field(default="", max_length=300)
    treatment_description: str = Field(default="", max_length=1200)
    closing_text: str = Field(default="", max_length=600)
    introduction_template: str = Field(default="", max_length=1600)
    director_name: str = Field(default="", max_length=160)
    director_role: str = Field(default="Director Greenway", max_length=120)
    director_email: str = Field(default="", max_length=180)
    director_phone: str = Field(default="", max_length=50)
    signature_data_url: str | None = Field(default=None, max_length=220_000)


class DisposalCertificateRead(DisposalCertificateListItem):
    model_config = ConfigDict(from_attributes=True)
    file_size: int
