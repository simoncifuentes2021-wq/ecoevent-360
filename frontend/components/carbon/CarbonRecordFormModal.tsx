"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { carbonCategories, carbonScopes, units } from "@/components/carbon/CarbonFilters";
import { EmissionEstimateBox } from "@/components/carbon/EmissionEstimateBox";
import type { CarbonFactor, CarbonRecord, CarbonRecordCreate, CarbonRecordUpdate } from "@/types/carbon";
import type { Evidence } from "@/types/evidence";

const schema = z.object({
  category: z.string().min(1, "La categoria es obligatoria"),
  scope: z.string().optional(),
  source: z.string().min(1, "La fuente es obligatoria"),
  activity_value: z.coerce.number().min(0.01, "El valor debe ser mayor que 0"),
  activity_unit: z.string().min(1, "La unidad es obligatoria"),
  factor_id: z.string().optional(),
  emission_factor_value: z.coerce.number().min(0).optional(),
  evidence_id: z.string().optional(),
  recorded_at: z.string().optional(),
  notes: z.string().optional()
});

export function CarbonRecordFormModal({ record, factors, evidences, loading, onClose, onSubmit }: { record?: CarbonRecord | null; factors: CarbonFactor[]; evidences: Evidence[]; loading?: boolean; onClose: () => void; onSubmit: (data: CarbonRecordCreate | CarbonRecordUpdate) => Promise<void> }) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      category: record?.category || "ENERGY",
      scope: record?.scope || "SCOPE_2",
      source: record?.source || record?.description || "",
      activity_value: Number(record?.activity_value || 0),
      activity_unit: record?.activity_unit || "kWh",
      factor_id: record?.factor_id || record?.emission_factor_id || "",
      emission_factor_value: Number(record?.emission_factor_value || record?.factor?.factor_value || record?.emission_factor?.factor_value || 0),
      evidence_id: record?.evidence_id || "",
      recorded_at: record?.recorded_at ? record.recorded_at.slice(0, 16) : "",
      notes: record?.notes || ""
    }
  });
  const selectedFactor = factors.find((factor) => factor.id === watch("factor_id"));
  const factorValue = useMemo(() => Number(selectedFactor?.factor_value ?? selectedFactor?.factor_kgco2e ?? watch("emission_factor_value") ?? 0), [selectedFactor, watch]);
  const activityValue = Number(watch("activity_value") || 0);

  function submit(values: z.infer<typeof schema>) {
    return onSubmit({
      category: values.category,
      scope: values.scope as CarbonRecordCreate["scope"],
      source: values.source,
      description: values.source,
      activity_value: values.activity_value,
      activity_unit: values.activity_unit,
      factor_id: values.factor_id || null,
      emission_factor_id: values.factor_id || null,
      emission_factor_value: factorValue || values.emission_factor_value || null,
      kg_co2e: activityValue && factorValue ? activityValue * factorValue : null,
      evidence_id: values.evidence_id || null,
      recorded_at: values.recorded_at || null,
      notes: values.notes || null
    });
  }

  return <ModalShell title={record ? "Editar registro carbono" : "Agregar registro carbono"} description="Registra actividad y factor para estimar kgCO2e." onClose={onClose}><form className="space-y-4" onSubmit={handleSubmit(submit)}><div className="grid gap-3 md:grid-cols-2"><label className="grid gap-2 text-sm font-semibold">Categoria<select className="h-12 rounded-2xl border px-4" {...register("category")}>{carbonCategories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label><label className="grid gap-2 text-sm font-semibold">Alcance<select className="h-12 rounded-2xl border px-4" {...register("scope")}>{carbonScopes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label><label className="grid gap-2 text-sm font-semibold">Fuente<Input {...register("source")} />{errors.source ? <span className="text-xs text-rose-600">{errors.source.message}</span> : null}</label><label className="grid gap-2 text-sm font-semibold">Actividad<Input type="number" step="0.01" {...register("activity_value")} />{errors.activity_value ? <span className="text-xs text-rose-600">{errors.activity_value.message}</span> : null}</label><label className="grid gap-2 text-sm font-semibold">Unidad<select className="h-12 rounded-2xl border px-4" {...register("activity_unit")}>{units.map((unit) => <option key={unit} value={unit}>{unit}</option>)}</select></label><label className="grid gap-2 text-sm font-semibold">Factor<select className="h-12 rounded-2xl border px-4" {...register("factor_id")}><option value="">Manual</option>{factors.map((factor) => <option key={factor.id} value={factor.id}>{factor.name} ({factor.unit})</option>)}</select></label><label className="grid gap-2 text-sm font-semibold">Factor manual<Input type="number" step="0.000001" {...register("emission_factor_value")} /></label><label className="grid gap-2 text-sm font-semibold">Evidencia<select className="h-12 rounded-2xl border px-4" {...register("evidence_id")}><option value="">Sin evidencia</option>{evidences.map((evidence) => <option key={evidence.id} value={evidence.id}>{evidence.description || evidence.filename || evidence.id}</option>)}</select></label></div><label className="grid gap-2 text-sm font-semibold">Fecha<Input type="datetime-local" {...register("recorded_at")} /></label><label className="grid gap-2 text-sm font-semibold">Notas<Input {...register("notes")} /></label><EmissionEstimateBox activityValue={activityValue} factorValue={factorValue} /><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={loading} type="submit">{loading ? "Guardando..." : "Guardar"}</Button></div></form></ModalShell>;
}
