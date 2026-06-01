import type { Evidence } from "@/types/evidence";
import type { User } from "@/types/user";
import type { Zone } from "@/types/zone";

export type FuelType = "DIESEL" | "GASOLINE" | "LPG" | "NATURAL_GAS" | "BIODIESEL" | "OTHER";
export type EnergySource = "GRID" | "GENERATOR" | "SOLAR" | "BATTERY" | "OTHER";
export type WaterSource = "NETWORK" | "TRUCK" | "BOTTLED" | "REUSED" | "OTHER";

type BaseRecord = {
  id: string;
  event_id: string;
  zone_id?: string | null;
  zone?: Pick<Zone, "id" | "name"> | null;
  evidence_id?: string | null;
  evidence?: Pick<Evidence, "id" | "file_url" | "file_type" | "description"> | null;
  recorded_by?: string | null;
  recorder?: Pick<User, "id" | "full_name" | "email"> | null;
  recorded_at?: string | null;
  created_at?: string;
  notes?: string | null;
};

export type FuelRecord = BaseRecord & { fuel_type: FuelType | string; quantity: number | string; unit: string; vehicle_or_equipment?: string | null };
export type EnergyRecord = BaseRecord & { energy_source: EnergySource | string; kwh: number | string };
export type WaterRecord = BaseRecord & { water_source: WaterSource | string; volume_m3: number | string };

export type FuelRecordCreate = { zone_id?: string | null; fuel_type: FuelType | string; quantity: number; unit: string; vehicle_or_equipment?: string | null; evidence_id?: string | null; recorded_at?: string | null; notes?: string | null };
export type EnergyRecordCreate = { zone_id?: string | null; energy_source: EnergySource | string; kwh: number; evidence_id?: string | null; recorded_at?: string | null; notes?: string | null };
export type WaterRecordCreate = { zone_id?: string | null; water_source: WaterSource | string; volume_m3: number; evidence_id?: string | null; recorded_at?: string | null; notes?: string | null };

export type FuelRecordUpdate = Partial<FuelRecordCreate>;
export type EnergyRecordUpdate = Partial<EnergyRecordCreate>;
export type WaterRecordUpdate = Partial<WaterRecordCreate>;
