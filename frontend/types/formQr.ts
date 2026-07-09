export type FormQrType = "FORM" | "FORM_LANGUAGE" | "BIKE_ZONE_PERSONAL";

export type FormQrCode = {
  id: string;
  form_id: string;
  event_id: string;
  session_id?: string | null;
  label: string;
  target_url: string;
  qr_type: FormQrType;
  language?: string | null;
  file_url?: string | null;
  format: string;
  created_by?: string | null;
  created_at: string;
};

export type FormQrCreate = {
  label: string;
  qr_type: FormQrType;
  language?: string | null;
  force?: boolean;
};
