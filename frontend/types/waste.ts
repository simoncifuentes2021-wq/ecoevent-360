import type { Evidence } from "@/types/evidence";
import type { User } from "@/types/user";
import type { Zone } from "@/types/zone";

export type WasteDestination = "RECYCLING" | "COMPOSTING" | "LANDFILL" | "RECOVERY" | "SPECIAL_DISPOSAL" | "OTHER";
export type WasteTypeCode = "PLASTIC" | "CARDBOARD" | "GLASS" | "ALUMINUM" | "ORGANIC" | "GENERAL" | "HAZARDOUS" | "OTHER";

export type WasteType = {
  id: string;
  name: string;
  description?: string | null;
  is_recyclable?: boolean;
  created_at?: string;
};

export type WasteRecord = {
  id: string;
  event_id: string;
  zone_id?: string | null;
  zone?: Pick<Zone, "id" | "name"> | null;
  waste_type_id?: string | null;
  waste_type?: WasteType | WasteTypeCode | string | null;
  weight_kg: number | string;
  destination: WasteDestination;
  destination_detail?: string | null;
  recorded_by?: string | null;
  recorder?: Pick<User, "id" | "full_name" | "email"> | null;
  evidence_id?: string | null;
  evidence?: Pick<Evidence, "id" | "file_url" | "file_type" | "description"> | null;
  recorded_at?: string | null;
  created_at?: string;
  notes?: string | null;
};

export type WasteRecordCreate = {
  zone_id?: string | null;
  waste_type_id?: string | null;
  waste_type?: WasteTypeCode | string | null;
  weight_kg: number;
  destination: WasteDestination;
  destination_detail?: string | null;
  evidence_id?: string | null;
  recorded_at?: string | null;
  notes?: string | null;
};

export type WasteRecordUpdate = Partial<WasteRecordCreate>;

export type WasteChartItem = {
  name: string;
  value: number;
  kg: number;
  percentage?: number;
};

export type WasteSummary = {
  total_kg: number;
  recovered_kg: number;
  recycled_kg?: number;
  organic_kg?: number;
  landfill_kg: number;
  recycling_rate?: number;
  recovery_rate: number;
  records_count?: number;
  by_type: WasteChartItem[];
  by_destination: WasteChartItem[];
  by_zone: WasteChartItem[];
};

export type WasteTypeCreate = {
  name: string;
  description?: string | null;
  is_recyclable?: boolean;
};

export type WasteTypeUpdate = Partial<WasteTypeCreate>;
