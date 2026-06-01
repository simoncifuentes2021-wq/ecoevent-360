import type { Evidence } from "@/types/evidence";
import type { User } from "@/types/user";

export type CarbonScope = "SCOPE_1" | "SCOPE_2" | "SCOPE_3";
export type CarbonCategory = "TRANSPORT" | "ENERGY" | "WASTE" | "WATER" | "MATERIALS" | "FOOD" | "ACCOMMODATION" | "OTHER";

export type CarbonFactor = {
  id: string;
  name: string;
  category: CarbonCategory | string;
  unit: string;
  factor_value?: number | string | null;
  factor_kgco2e?: number | string | null;
  scope?: CarbonScope | null;
  source?: string | null;
  source_url?: string | null;
  year?: number | null;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
};

export type CarbonRecord = {
  id: string;
  event_id: string;
  category: CarbonCategory | string;
  scope?: CarbonScope | null;
  source?: string | null;
  description?: string | null;
  activity_value: number | string;
  activity_unit: string;
  emission_factor_id?: string | null;
  factor_id?: string | null;
  emission_factor?: CarbonFactor | null;
  factor?: CarbonFactor | null;
  emission_factor_value?: number | string | null;
  emissions_kgco2e?: number | string | null;
  kg_co2e?: number | string | null;
  evidence_id?: string | null;
  evidence?: Pick<Evidence, "id" | "file_url" | "file_type" | "description"> | null;
  recorded_by?: string | null;
  recorder?: Pick<User, "id" | "full_name" | "email"> | null;
  recorded_at?: string | null;
  created_at?: string;
  notes?: string | null;
};

export type CarbonRecordCreate = {
  category: CarbonCategory | string;
  scope?: CarbonScope | null;
  source?: string | null;
  description?: string | null;
  activity_value: number;
  activity_unit: string;
  emission_factor_id?: string | null;
  factor_id?: string | null;
  emission_factor_value?: number | null;
  kg_co2e?: number | null;
  evidence_id?: string | null;
  recorded_at?: string | null;
  notes?: string | null;
};

export type CarbonRecordUpdate = Partial<CarbonRecordCreate>;

export type CarbonChartItem = { name: string; value: number; kg: number };

export type CarbonSummary = {
  total_kg_co2e: number;
  total_ton_co2e: number;
  kg_co2e_per_attendee: number;
  records_count: number;
  by_category: CarbonChartItem[];
  by_scope: CarbonChartItem[];
  by_source: CarbonChartItem[];
  by_date: CarbonChartItem[];
};

export type CarbonFactorCreate = {
  name: string;
  category: CarbonCategory | string;
  unit: string;
  factor_value: number;
  source?: string | null;
  source_url?: string | null;
  year?: number | null;
  is_active?: boolean;
  scope?: CarbonScope | null;
};

export type CarbonFactorUpdate = Partial<CarbonFactorCreate>;
