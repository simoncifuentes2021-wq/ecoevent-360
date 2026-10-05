import { MapPin } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { Event } from "@/types/event";

export function ClientEventLogisticsCard({ event }: { event: Event }) {
  const location = [event.location_name, event.city, event.region, event.country].filter(Boolean).join(", ");
  const latitude = event.latitude === null || event.latitude === undefined || event.latitude === "" ? "No informada" : String(event.latitude);
  const longitude = event.longitude === null || event.longitude === undefined || event.longitude === "" ? "No informada" : String(event.longitude);

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-center gap-2 text-slate-900">
          <MapPin className="h-5 w-5 text-emerald-700" />
          <h2 className="text-lg font-bold">Datos logísticos</h2>
        </div>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <LogisticsInfo label="Ubicación" value={location || "Sin ubicación registrada"} />
          <LogisticsInfo label="Dirección" value={event.address || "Sin dirección registrada"} />
          <LogisticsInfo label="Latitud" value={latitude} />
          <LogisticsInfo label="Longitud" value={longitude} />
        </div>
      </CardContent>
    </Card>
  );
}

function LogisticsInfo({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-bold uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-slate-800">{value}</p>
    </div>
  );
}
