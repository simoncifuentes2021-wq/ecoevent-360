"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { carbonCategories, carbonScopes, normalizeCarbonCategory } from "@/components/carbon/CarbonFilters";
import { EmissionEstimateBox } from "@/components/carbon/EmissionEstimateBox";
import { getCarbonFactors } from "@/lib/api/carbonFactors";
import type { CarbonFactor, CarbonRecord, CarbonRecordCreate, CarbonRecordUpdate } from "@/types/carbon";
import type { Evidence } from "@/types/evidence";

const schema = z.object({
  category: z.string().min(1, "La categoria es obligatoria"),
  scope: z.string().optional(),
  source: z.string().min(1, "La fuente es obligatoria"),
  activity_value: z.coerce.number().min(0.01, "El valor debe ser mayor que 0"),
  factor_id: z.string().min(1, "Selecciona un factor de emision"),
  evidence_id: z.string().optional(),
  recorded_at: z.string().optional(),
  notes: z.string().optional()
});

export function CarbonRecordFormModal({ record, factors, evidences, loading, onClose, onSubmit }: { record?: CarbonRecord | null; factors: CarbonFactor[]; evidences: Evidence[]; loading?: boolean; onClose: () => void; onSubmit: (data: CarbonRecordCreate | CarbonRecordUpdate) => Promise<void> }) {
  const [fallbackFactors, setFallbackFactors] = useState<CarbonFactor[]>([]);
  const [factorLoadError, setFactorLoadError] = useState<string | null>(null);
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      category: record?.category || "ENERGY",
      scope: record?.scope || "SCOPE_2",
      source: record?.source || record?.description || "",
      activity_value: Number(record?.activity_value || 0),
      factor_id: record?.factor_id || record?.emission_factor_id || "",
      evidence_id: record?.evidence_id || "",
      recorded_at: record?.recorded_at ? record.recorded_at.slice(0, 16) : "",
      notes: record?.notes || ""
    }
  });
  const category = watch("category");
  const factorId = watch("factor_id");
  const availableFactors = factors.length > 0 ? factors : fallbackFactors;
  const activeFactors = useMemo(() => availableFactors.filter((factor) => factor.is_active !== false), [availableFactors]);
  const categoryFactors = useMemo(() => activeFactors.filter((factor) => normalizeCarbonCategory(factor.category) === category), [activeFactors, category]);
  const selectableFactors = categoryFactors.length > 0 ? categoryFactors : activeFactors;
  const hasCategoryMatch = categoryFactors.length > 0;
  const selectedFactor = availableFactors.find((factor) => factor.id === factorId);
  const factorValue = useMemo(() => Number(selectedFactor?.factor_value ?? selectedFactor?.factor_kgco2e ?? 0), [selectedFactor]);
  const activityValue = Number(watch("activity_value") || 0);
  const selectedUnit = selectedFactor?.unit || "";
  const fieldClass = "grid min-w-0 gap-2 text-sm font-semibold";
  const selectClass = "h-12 w-full min-w-0 rounded-2xl border px-4";

  useEffect(() => {
    if (factors.length > 0) {
      setFallbackFactors([]);
      setFactorLoadError(null);
      return;
    }
    let cancelled = false;
    getCarbonFactors({ page: 1, limit: 100 })
      .then((data) => {
        if (!cancelled) {
          setFallbackFactors(data.items);
          setFactorLoadError(null);
        }
      })
      .catch((error) => {
        if (!cancelled) setFactorLoadError(error instanceof Error ? error.message : "No se pudo cargar el catalogo de factores.");
      });
    return () => {
      cancelled = true;
    };
  }, [factors.length]);

  useEffect(() => {
    if (factorId && selectableFactors.some((factor) => factor.id === factorId)) return;
    setValue("factor_id", selectableFactors[0]?.id || "");
  }, [factorId, selectableFactors, setValue]);

  function submit(values: z.infer<typeof schema>) {
    return onSubmit({
      category: values.category,
      scope: values.scope as CarbonRecordCreate["scope"],
      source: values.source,
      description: values.source,
      activity_value: values.activity_value,
      activity_unit: selectedUnit,
      factor_id: values.factor_id,
      emission_factor_id: values.factor_id,
      emission_factor_value: factorValue || null,
      kg_co2e: activityValue && factorValue ? activityValue * factorValue : null,
      evidence_id: values.evidence_id || null,
      recorded_at: values.recorded_at || null,
      notes: values.notes || null
    });
  }

  return (
    <ModalShell
      title={record ? "Editar registro carbono" : "Agregar registro carbono"}
      description="Registra actividad y factor para estimar kgCO2e."
      onClose={onClose}
      size="lg"
    >
      <form className="space-y-5" onSubmit={handleSubmit(submit)}>
        <div className="grid min-w-0 gap-4 md:grid-cols-2">
          <label className={fieldClass}>
            Categoria
            <select className={selectClass} {...register("category")}>
              {carbonCategories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label className={fieldClass}>
            Alcance
            <select className={selectClass} {...register("scope")}>
              {carbonScopes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label className={fieldClass}>
            Fuente
            <Input className="h-12 rounded-2xl px-4 text-base" placeholder="Ej: Electricidad recinto" {...register("source")} />
            {errors.source ? <span className="text-xs text-rose-600">{errors.source.message}</span> : null}
          </label>
          <label className={fieldClass}>
            Actividad
            <Input className="h-12 rounded-2xl px-4 text-base" type="number" step="0.01" {...register("activity_value")} />
            {errors.activity_value ? <span className="text-xs text-rose-600">{errors.activity_value.message}</span> : null}
          </label>
          <label className={`${fieldClass} md:col-span-2`}>
            Factor
            <select className={selectClass} {...register("factor_id")}>
              <option value="">Selecciona un factor</option>
              {selectableFactors.map((factor) => <option key={factor.id} value={factor.id}>{factor.name} ({factor.unit})</option>)}
            </select>
            {errors.factor_id ? <span className="text-xs text-rose-600">{errors.factor_id.message}</span> : null}
            {factorLoadError ? <span className="text-xs text-rose-600">{factorLoadError}</span> : null}
            {activeFactors.length === 0 && !factorLoadError ? <span className="text-xs text-amber-700">Cargando factores activos...</span> : null}
            {activeFactors.length > 0 && !hasCategoryMatch ? <span className="text-xs text-amber-700">No hay factores activos para esta categoria; se muestran todos los activos.</span> : null}
          </label>
          <label className={fieldClass}>
            Unidad
            <Input className="h-12 rounded-2xl px-4 text-base" readOnly value={selectedUnit || "Selecciona un factor"} />
          </label>
          <label className={fieldClass}>
            Factor kgCO2e/{selectedUnit || "unidad"}
            <Input className="h-12 rounded-2xl px-4 text-base" readOnly value={factorValue || 0} />
          </label>
          <label className={fieldClass}>
            Evidencia
            <select className={selectClass} {...register("evidence_id")}>
              <option value="">Sin evidencia</option>
              {evidences.map((evidence) => <option key={evidence.id} value={evidence.id}>{evidence.description || evidence.filename || evidence.id}</option>)}
            </select>
          </label>
          <label className={fieldClass}>
            Fecha
            <Input className="h-12 rounded-2xl px-4 text-base" type="datetime-local" {...register("recorded_at")} />
          </label>
          <label className={`${fieldClass} md:col-span-2`}>
            Notas
            <Input className="h-12 rounded-2xl px-4 text-base" {...register("notes")} />
          </label>
        </div>
        <EmissionEstimateBox activityValue={activityValue} factorValue={factorValue} />
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={loading || !selectedFactor} type="submit">{loading ? "Guardando..." : "Guardar"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}
