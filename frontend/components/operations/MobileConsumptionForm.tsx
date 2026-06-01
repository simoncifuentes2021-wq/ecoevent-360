"use client";
import { useState } from "react";
import { EnergyRecordFormModal } from "@/components/operations/EnergyRecordFormModal";
import { FuelRecordFormModal } from "@/components/operations/FuelRecordFormModal";
import { WaterRecordFormModal } from "@/components/operations/WaterRecordFormModal";
import { Button } from "@/components/ui/button";
import type { EnergyRecordCreate, FuelRecordCreate, WaterRecordCreate } from "@/types/operations";
import type { Zone } from "@/types/zone";
type Kind = "fuel" | "energy" | "water";
export function MobileConsumptionForm({ zones, loading, onCancel, onFuel, onEnergy, onWater }: { zones: Zone[]; loading?: boolean; onCancel: () => void; onFuel: (data: FuelRecordCreate) => Promise<void>; onEnergy: (data: EnergyRecordCreate) => Promise<void>; onWater: (data: WaterRecordCreate) => Promise<void> }) {
  const [kind, setKind] = useState<Kind>("fuel");
  return <div className="space-y-4"><div className="grid grid-cols-3 gap-2"><Button variant={kind === "fuel" ? "primary" : "secondary"} onClick={() => setKind("fuel")}>Combustible</Button><Button variant={kind === "energy" ? "primary" : "secondary"} onClick={() => setKind("energy")}>Energia</Button><Button variant={kind === "water" ? "primary" : "secondary"} onClick={() => setKind("water")}>Agua</Button></div>{kind === "fuel" ? <FuelRecordFormModal loading={loading} zones={zones} onClose={onCancel} onSubmit={onFuel} /> : null}{kind === "energy" ? <EnergyRecordFormModal loading={loading} zones={zones} onClose={onCancel} onSubmit={onEnergy} /> : null}{kind === "water" ? <WaterRecordFormModal loading={loading} zones={zones} onClose={onCancel} onSubmit={onWater} /> : null}</div>;
}
