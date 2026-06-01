export type Service = {
  id: string;
  name: string;
  category: string | null;
  description: string | null;
  unit: string | null;
  base_price: string | number | null;
  is_active: boolean;
  created_at: string;
};

export type ServiceCreate = {
  name: string;
  category?: string | null;
  description?: string | null;
  unit?: string | null;
  base_price?: number | null;
};

export type ServiceUpdate = Partial<ServiceCreate> & {
  is_active?: boolean;
};
