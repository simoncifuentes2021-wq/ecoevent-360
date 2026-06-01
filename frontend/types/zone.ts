export type Zone = {
  id: string;
  event_id: string;
  name: string;
  description?: string | null;
  qr_code_url?: string | null;
  created_at?: string;
};

export type ZoneCreate = {
  name: string;
  description?: string | null;
};

export type ZoneUpdate = Partial<ZoneCreate>;
