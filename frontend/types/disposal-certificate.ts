export type DisposalCertificateMaterialContext = {
  waste_type_id: string;
  name: string;
  received_kg: number | string;
};

export type DisposalCertificateListItem = {
  id: string;
  certificate_number: string;
  certificate_date: string;
  total_kg: number | string;
  recipient_name: string;
  receiving_facility_name: string;
  sha256: string;
  generated_at: string;
};

export type DisposalCertificateContext = {
  event_id: string;
  event_name: string;
  recipient_name: string;
  recipient_rut: string | null;
  materials: DisposalCertificateMaterialContext[];
  certificates: DisposalCertificateListItem[];
};

export type DisposalCertificateDefaults = {
  issuer_name: string;
  issuer_rut: string;
  issuer_address: string;
  introduction_template: string;
  treatment_description: string;
  closing_text: string;
  director_name: string;
  director_role: string;
  director_email: string;
  director_phone: string;
  signature_data_url: string;
};

export type DisposalCertificateCreate = {
  recipient_name: string;
  recipient_rut: string;
  event_name: string;
  materials: { waste_type_id: string; final_weight_kg: number }[];
};
