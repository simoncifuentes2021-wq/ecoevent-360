import { MapPin, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Zone } from "@/types/zone";

export function ZoneCard({ zone, canManage, onEdit, onDelete }: { zone: Zone; canManage: boolean; onEdit: (zone: Zone) => void; onDelete: (zone: Zone) => void }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
            <MapPin className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold text-slate-950">{zone.name}</p>
            <p className="mt-1 text-sm text-slate-600">{zone.description || "Zona operativa del evento."}</p>
            {zone.qr_code_url ? <p className="mt-2 text-xs text-emerald-700">QR preparado</p> : null}
          </div>
        </div>
        {canManage ? (
          <div className="flex gap-1">
            <Button size="sm" type="button" variant="ghost" onClick={() => onEdit(zone)}><Pencil className="h-4 w-4" /></Button>
            <Button size="sm" type="button" variant="ghost" onClick={() => onDelete(zone)}><Trash2 className="h-4 w-4" /></Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
