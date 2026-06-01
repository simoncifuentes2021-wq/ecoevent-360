"use client";
import { useState } from "react";
import { EnergyRecordsTab } from "@/components/operations/EnergyRecordsTab";
import { FuelRecordsTab } from "@/components/operations/FuelRecordsTab";
import { WaterRecordsTab } from "@/components/operations/WaterRecordsTab";
import { Button } from "@/components/ui/button";
import type { UserRole } from "@/types/roles";
import { canCreateOperationalConsumption } from "@/lib/permissions";
export function OperationalConsumptionTabs({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [tab, setTab] = useState("fuel"); const canCreate = canCreateOperationalConsumption(role);
  return <div className="space-y-4"><div className="flex gap-2 overflow-x-auto"><Button size="sm" variant={tab === "fuel" ? "primary" : "secondary"} onClick={() => setTab("fuel")}>Combustible</Button><Button size="sm" variant={tab === "energy" ? "primary" : "secondary"} onClick={() => setTab("energy")}>Energia</Button><Button size="sm" variant={tab === "water" ? "primary" : "secondary"} onClick={() => setTab("water")}>Agua</Button></div>{tab === "fuel" ? <FuelRecordsTab canCreate={canCreate} eventId={eventId} /> : null}{tab === "energy" ? <EnergyRecordsTab canCreate={canCreate} eventId={eventId} /> : null}{tab === "water" ? <WaterRecordsTab canCreate={canCreate} eventId={eventId} /> : null}</div>;
}
