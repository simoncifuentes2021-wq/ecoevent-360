"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { FuelRecordCreate } from "@/types/operations";
import type { Zone } from "@/types/zone";
const schema = z.object({ fuel_type: z.string().min(1), quantity: z.coerce.number().min(0.01), unit: z.string().min(1), vehicle_or_equipment: z.string().optional(), zone_id: z.string().optional(), notes: z.string().optional() });
export function FuelRecordFormModal({ zones, loading, onClose, onSubmit }: { zones: Zone[]; loading?: boolean; onClose: () => void; onSubmit: (data: FuelRecordCreate) => Promise<void> }) {
  const { register, handleSubmit } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { fuel_type: "DIESEL", unit: "L" } });
  return <ModalShell title="Registrar combustible" onClose={onClose}><form className="space-y-4" onSubmit={handleSubmit((v) => onSubmit({ ...v, zone_id: v.zone_id || null, vehicle_or_equipment: v.vehicle_or_equipment || null, notes: v.notes || null }))}><div className="grid gap-3 md:grid-cols-2"><label className="grid gap-2 text-sm font-semibold">Tipo<select className="h-12 rounded-2xl border px-4" {...register("fuel_type")}><option>DIESEL</option><option>GASOLINE</option><option>LPG</option><option>NATURAL_GAS</option><option>BIODIESEL</option><option>OTHER</option></select></label><label className="grid gap-2 text-sm font-semibold">Cantidad<Input type="number" step="0.01" {...register("quantity")} /></label><label className="grid gap-2 text-sm font-semibold">Unidad<Input {...register("unit")} /></label><label className="grid gap-2 text-sm font-semibold">Zona<select className="h-12 rounded-2xl border px-4" {...register("zone_id")}><option value="">Sin zona</option>{zones.map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}</select></label></div><label className="grid gap-2 text-sm font-semibold">Equipo<Input {...register("vehicle_or_equipment")} /></label><label className="grid gap-2 text-sm font-semibold">Notas<Input {...register("notes")} /></label><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={loading}>Guardar</Button></div></form></ModalShell>;
}
