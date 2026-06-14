"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { CameraFilePicker } from "@/components/files/CameraFilePicker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createEvidence } from "@/lib/api/evidences";
import { destinations } from "@/components/waste/WasteFilters";
import type { Evidence } from "@/types/evidence";
import type { WasteDestination, WasteRecord, WasteRecordCreate, WasteRecordUpdate, WasteType } from "@/types/waste";
import type { Zone } from "@/types/zone";

const schema = z.object({
  zone_id: z.string().optional(),
  waste_type_key: z.string().min(1, "El tipo de residuo es obligatorio"),
  weight_kg: z.preprocess(
    (value) => (value === "" || value === null ? undefined : Number(value)),
    z
      .number({ required_error: "El peso es obligatorio", invalid_type_error: "El peso es obligatorio" })
      .min(0.01, "El peso debe ser mayor que 0")
  ),
  destination: z.enum(["RECYCLING", "COMPOSTING", "LANDFILL", "RECOVERY", "SPECIAL_DISPOSAL", "OTHER"], {
    required_error: "El destino es obligatorio",
    invalid_type_error: "El destino es obligatorio"
  }),
  destination_detail: z.string().optional(),
  evidence_id: z.string().optional(),
  recorded_at: z.string().optional(),
  notes: z.string().optional()
});

function currentType(record?: WasteRecord | null) {
  return record?.waste_type_id || (typeof record?.waste_type === "string" ? record.waste_type : "");
}

function evidenceLabel(item: Evidence) {
  return item.description || [item.file_type, item.created_at ? new Date(item.created_at).toLocaleString("es-CL") : null].filter(Boolean).join(" · ") || "Evidencia sin descripción";
}

export function WasteRecordFormModal({ record, eventId, zones, evidences, wasteTypes, loading, onClose, onSubmit }: { record?: WasteRecord | null; eventId?: string; zones: Zone[]; evidences: Evidence[]; wasteTypes: WasteType[]; loading?: boolean; onClose: () => void; onSubmit: (data: WasteRecordCreate | WasteRecordUpdate) => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      zone_id: record?.zone_id || "",
      waste_type_key: currentType(record),
      weight_kg: record?.weight_kg ? Number(record.weight_kg) : undefined,
      destination: record?.destination || "RECYCLING",
      destination_detail: record?.destination_detail || "",
      evidence_id: record?.evidence_id || "",
      recorded_at: record?.recorded_at ? record.recorded_at.slice(0, 16) : "",
      notes: record?.notes || ""
    }
  });
  const selectedEvidenceId = watch("evidence_id");
  const selectedEvidence = useMemo(() => evidences.find((item) => item.id === selectedEvidenceId), [evidences, selectedEvidenceId]);

  async function submit(values: z.infer<typeof schema>) {
    setUploadError(null);
    let evidenceId = values.evidence_id || null;
    if (file && eventId) {
      setUploading(true);
      try {
        const formData = new FormData();
        formData.append("event_id", eventId);
        formData.append("description", `Residuo: ${wasteTypes.find((type) => type.id === values.waste_type_key)?.name || "registro"}`);
        formData.append("file", file);
        const evidence = await createEvidence(formData);
        evidenceId = evidence.id;
      } catch (err) {
        setUploadError(err instanceof Error ? err.message : "No se pudo subir la foto.");
        setUploading(false);
        return;
      } finally {
        setUploading(false);
      }
    }
    return onSubmit({
      zone_id: values.zone_id || null,
      waste_type_id: values.waste_type_key,
      weight_kg: values.weight_kg,
      destination: values.destination as WasteDestination,
      destination_detail: values.destination_detail || null,
      evidence_id: evidenceId,
      recorded_at: values.recorded_at || null,
      notes: values.notes || null
    });
  }

  return (
    <ModalShell title={record ? "Editar residuo" : "Registrar residuo"} description="Registra kg, tipo, destino, zona y respaldo ambiental." onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit(submit)}>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid min-w-0 gap-2 text-sm font-semibold">Zona<select className="h-12 w-full min-w-0 rounded-2xl border px-4" {...register("zone_id")}><option value="">Sin zona</option>{zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}</select></label>
          <label className="grid min-w-0 gap-2 text-sm font-semibold">Tipo<select className="h-12 w-full min-w-0 rounded-2xl border px-4" {...register("waste_type_key")}><option value="">Seleccionar</option>{wasteTypes.map((type) => <option key={type.id} value={type.id}>{type.name}</option>)}</select>{errors.waste_type_key ? <span className="text-xs text-rose-600">{errors.waste_type_key.message}</span> : null}</label>
          <label className="grid min-w-0 gap-2 text-sm font-semibold">Peso kg<Input min={0} step="0.01" type="number" {...register("weight_kg")} />{errors.weight_kg ? <span className="text-xs text-rose-600">{errors.weight_kg.message}</span> : null}</label>
          <label className="grid min-w-0 gap-2 text-sm font-semibold">Destino<select className="h-12 w-full min-w-0 rounded-2xl border px-4" {...register("destination")}>{destinations.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>{errors.destination ? <span className="text-xs text-rose-600">{errors.destination.message}</span> : null}</label>
          <label className="grid min-w-0 gap-2 text-sm font-semibold md:col-span-2">Fecha registro<Input className="w-full min-w-0" type="datetime-local" {...register("recorded_at")} /></label>
        </div>
        <section className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <div>
            <p className="text-sm font-bold text-slate-900">Evidencia existente</p>
            <p className="text-xs font-medium text-slate-500">Opcional. Elige una imagen ya subida o sube una nueva más abajo.</p>
          </div>
          {file ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">Hay una foto nueva seleccionada; se usará esa en vez de una evidencia existente.</p> : null}
          <div className="flex gap-3 overflow-x-auto pb-1">
            <button
              className={`grid h-28 w-32 shrink-0 place-items-center rounded-xl border border-dashed bg-white p-2 text-center text-xs font-semibold ${!selectedEvidenceId ? "border-emerald-500 text-emerald-700" : "border-slate-300 text-slate-500"}`}
              disabled={Boolean(file)}
              onClick={() => setValue("evidence_id", "")}
              type="button"
            >
              Sin evidencia existente
            </button>
            {evidences.map((item) => {
              const active = item.id === selectedEvidenceId;
              return (
                <button
                  className={`h-28 w-32 shrink-0 overflow-hidden rounded-xl border bg-white text-left ${active ? "border-emerald-500 ring-2 ring-emerald-100" : "border-slate-200"}`}
                  disabled={Boolean(file)}
                  key={item.id}
                  onClick={() => setValue("evidence_id", item.id)}
                  type="button"
                >
                  {item.file_type?.startsWith("image/") ? (
                    <img alt={evidenceLabel(item)} className="h-16 w-full object-cover" src={item.file_url} />
                  ) : (
                    <div className="grid h-16 place-items-center bg-white text-xs font-bold text-slate-600">PDF</div>
                  )}
                  <p className="line-clamp-2 px-2 py-1 text-xs font-semibold text-slate-700">{evidenceLabel(item)}</p>
                </button>
              );
            })}
          </div>
          {selectedEvidence && !file ? <p className="text-xs font-semibold text-emerald-700">Seleccionada: {evidenceLabel(selectedEvidence)}</p> : null}
        </section>
        {eventId ? (
          <label className="grid gap-2 rounded-2xl border border-slate-200 bg-white p-3 text-sm font-semibold">
            <span>Subir foto ahora</span>
            <CameraFilePicker onFile={(nextFile) => { setFile(nextFile); setValue("evidence_id", ""); }} />
            {file ? <span className="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800">Se subirá y asociará: {file.name}</span> : <span className="text-xs font-medium text-slate-500">Puedes tomar o seleccionar una foto directamente desde aquí.</span>}
            {uploadError ? <span className="text-xs font-semibold text-rose-600">{uploadError}</span> : null}
          </label>
        ) : null}
        <label className="grid gap-2 text-sm font-semibold">Detalle destino<Input {...register("destination_detail")} /></label>
        <label className="grid gap-2 text-sm font-semibold">Notas<Input {...register("notes")} /></label>
        {wasteTypes.length === 0 ? <p className="rounded-lg bg-amber-50 p-3 text-sm font-semibold text-amber-800">No hay tipos de residuos disponibles. Debes crear o cargar tipos de residuos antes de registrar.</p> : null}
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={loading || uploading || wasteTypes.length === 0} type="submit">{loading || uploading ? "Guardando..." : "Guardar"}</Button></div>
      </form>
    </ModalShell>
  );
}
