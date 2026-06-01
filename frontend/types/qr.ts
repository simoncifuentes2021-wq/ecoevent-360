import type { Zone } from "@/types/zone";

export type QrCode = {
  id: string;
  survey_id: string;
  zone_id?: string | null;
  zone?: Zone | null;
  label: string;
  target_url?: string | null;
  file_url?: string | null;
  image_url?: string | null;
  created_at?: string;
};

export type QrCodeCreate = {
  label: string;
  zone_id?: string | null;
  target_url?: string | null;
};
