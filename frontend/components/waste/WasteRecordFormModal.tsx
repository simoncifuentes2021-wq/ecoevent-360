"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { destinations, fallbackWasteTypes } from "@/components/waste/WasteFilters";
import type { Evidence } from "@/types/evidence";
import type { WasteDestination, WasteRecord, WasteRecordCreate, WasteRecordUpdate, WasteType } from "@/types/waste";
import type { Zone } from "@/types/zone";

const schema = z.object({
  zone_id: z.string().optional(),
  waste_type_key: z.string().min(1, "Selecciona un tipo"),
  weight_kg: z.coerce.number().min(0.01, "El peso debe ser mayor que 0"),
  destination: z.enum(["RECYCLING", "COMPOSTING", "LANDFILL", "RECOVERY", "SPECIAL_DISPOSAL", "OTHER"]),
  destination_detail: z.string().optional(),
  evidence_id: z.string().optional(),
  recorded_at: z.string().optional(),
  notes: z.string().optional()
});

function currentType(record?: WasteRecord | null) {
  return record?.waste_type_id || (typeof record?.waste_type === "string" ? record.waste_type : "");
}

export function WasteRecordFormModal({ record, zones, evidences, wasteTypes, loading, onClose, onSubmit }: { record?: WasteRecord | null; zones: Zone[]; evidences: Evidence[]; wasteTypes: WasteType[]; loading?: boolean; onClose: () => void; onSubmit: (data: WasteRecordCreate | WasteRecordUpdate) => Promise<void> }) {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      zone_id: record?.zone_id || "",
      waste_type_key: currentType(record),
      weight_kg: Number(record?.weight_kg || 0),
      destination: record?.destination || "RECYCLING",
      destination_detail: record?.destination_detail || "",
      evidence_id: record?.evidence_id || "",
      recorded_at: record?.recorded_at ? record.recorded_at.slice(0, 16) : "",
      notes: record?.notes || ""
    }
  });

  function submit(values: z.infer<typeof schema>) {
    const usesCatalog = wasteTypes.length > 0;
    return onSubmit({
      zone_id: values.zone_id || null,
      waste_type_id: usesCatalog ? values.waste_type_key : null,
      waste_type: usesCatalog ? null : values.waste_type_key,
      weight_kg: values.weight_kg,
      destination: values.destination as WasteDestination,
      destination_detail: values.destination_detail || null,
      evidence_id: values.evidence_id || null,
      recorded_at: values.recorded_at || null,
      notes: values.notes || null
    });
  }

  return (
    <ModalShell title={record ? "Editar residuo" : "Registrar residuo"} description="Registra kg, tipo, destino, zona y respaldo ambiental." onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit(submit)}>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">Zona<select className="h-12 rounded-2xl border px-4" {...register("zone_id")}><option value="">Sin zona</option>{zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}</select></label>
          <label className="grid gap-2 text-sm font-semibold">Tipo<select className="h-12 rounded-2xl border px-4" {...register("waste_type_key")}><option value="">Seleccionar</option>{(wasteTypes.length ? wasteTypes.map((type) => ({ label: type.name, value: type.id })) : fallbackWasteTypes).map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select>{errors.waste_type_key ? <span className="text-xs text-rose-600">{errors.waste_type_key.message}</span> : null}</label>
          <label className="grid gap-2 text-sm font-semibold">Peso kg<Input min={0} step="0.01" type="number" {...register("weight_kg")} />{errors.weight_kg ? <span className="text-xs text-rose-600">{errors.weight_kg.message}</span> : null}</label>
          <label className="grid gap-2 text-sm font-semibold">Destino<select className="h-12 rounded-2xl border px-4" {...register("destination")}>{destinations.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label className="grid gap-2 text-sm font-semibold">Evidencia<select className="h-12 rounded-2xl border px-4" {...register("evidence_id")}><option value="">Sin evidencia</option>{evidences.map((item) => <option key={item.id} value={item.id}>{item.description || item.filename || item.id}</option>)}</select></label>
          <label className="grid gap-2 text-sm font-semibold">Fecha registro<Input type="datetime-local" {...register("recorded_at")} /></label>
        </div>
        <label className="grid gap-2 text-sm font-semibold">Detalle destino<Input {...register("destination_detail")} /></label>
        <label className="grid gap-2 text-sm font-semibold">Notas<Input {...register("notes")} /></label>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={loading} type="submit">{loading ? "Guardando..." : "Guardar"}</Button></div>
      </form>
    </ModalShell>
  );
}
