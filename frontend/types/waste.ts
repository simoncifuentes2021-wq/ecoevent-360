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

export type WasteCollectionPoint = {
  id: string;
  event_id: string;
  zone_id: string | null;
  code: string;
  name: string;
  description: string | null;
  location_description: string | null;
  capacity_kg: number | string | null;
  qr_token?: string;
  is_active: boolean;
  record_count: number;
  total_kg: number | string;
  public_url: string | null;
  qr_data_url: string | null;
  allowed_waste_types: PublicWasteType[];
};

export type WasteCollectionRecord = {
  id: string;
  event_id: string;
  collection_point_id: string;
  collection_point_code: string;
  collection_point_name: string;
  waste_type_id: string;
  waste_type_name: string;
  weight_kg: number | string;
  submitter_name: string;
  submitter_rut_masked: string;
  client_generated_id: string;
  device_id: string | null;
  recorded_at: string;
  synced_at: string | null;
};

export type WasteCollectionSummary = {
  event_id: string;
  total_kg: number | string;
  recyclable_kg?: number | string;
  records_count: number;
  active_points: number;
  unique_submitters: number;
  by_type: { id: string; name: string; is_recyclable?: boolean; total_kg: number | string; records_count: number }[];
  by_point: { id: string; code: string; name: string; total_kg: number | string; records_count: number }[];
  eco_equivalences?: { kind: "FAMILY_DAYS" | "MATERIAL_UNITS"; waste_type_name: string | null; name: string; value: number | string; unit: string; reference_kg?: number | string }[];
};

export type PublicWasteType = { id: string; name: string; is_recyclable?: boolean | null };
export type PublicCollectionPoint = { event_id: string; form_status: "ACTIVE" | "CLOSED" | "DRAFT"; event_name: string; collection_points: { id: string; code: string; name: string; allowed_waste_types: PublicWasteType[] }[] };
export type PublicWasteSubmission = {
  client_generated_id: string;
  device_id: string;
  waste_type_id: string;
  collection_point_id: string;
  weight_kg: number;
  submitter_name: string;
  submitter_rut: string;
  recorded_at: string;
};

export type EventWastePublicForm = { event_id: string; token: string; status: "DRAFT" | "ACTIVE" | "CLOSED"; public_url: string | null; qr_data_url: string | null; opened_at: string | null; closed_at: string | null };

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
  id?: string | null;
  waste_type_id?: string | null;
  collection_point_id?: string | null;
  code?: string;
  source?: string;
  name: string;
  value: number;
  kg: number;
  collection_points_kg?: number;
  direct_kg?: number;
  percentage?: number;
  records_count?: number;
};

export type WasteSummarySourceTotals = { weight_kg: number; percentage: number; records_count: number };

export type WasteSummary = {
  total_kg: number;
  recovered_kg: number;
  special_disposal_kg: number;
  recycled_kg?: number;
  organic_kg?: number;
  landfill_kg: number;
  recycling_rate?: number;
  recovery_rate: number;
  records_count?: number;
  total_event_kg: number;
  total_records: number;
  waste_types_count: number;
  collection_points: WasteSummarySourceTotals;
  direct_records: WasteSummarySourceTotals;
  top_waste_type: WasteChartItem | null;
  top_collection_point: WasteChartItem | null;
  by_source: WasteChartItem[];
  by_collection_point: WasteChartItem[];
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
