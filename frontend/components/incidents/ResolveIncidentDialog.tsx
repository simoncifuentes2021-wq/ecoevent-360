"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import type { Evidence } from "@/types/evidence";
import type { IncidentResolve } from "@/types/incident";

const schema = z.object({
  solution: z.string().min(5, "Describe la solucion aplicada"),
  evidence_id: z.string().optional()
});

export function ResolveIncidentDialog({ evidences, loading, onClose, onConfirm }: { evidences: Evidence[]; loading?: boolean; onClose: () => void; onConfirm: (data: IncidentResolve) => Promise<void> }) {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });
  return (
    <ModalShell title="Resolver incidencia" description="Registra la solucion aplicada en terreno." onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit((values) => onConfirm({ solution: values.solution, evidence_id: values.evidence_id || null }))}>
        <label className="grid gap-2 text-sm font-semibold">Solucion<textarea className="min-h-28 rounded-2xl border px-4 py-3" {...register("solution")} />{errors.solution ? <span className="text-xs text-rose-600">{errors.solution.message}</span> : null}</label>
        <label className="grid gap-2 text-sm font-semibold">Evidencia asociada<select className="h-12 rounded-2xl border px-4" {...register("evidence_id")}><option value="">Sin evidencia</option>{evidences.map((item) => <option key={item.id} value={item.id}>{item.description || item.filename || item.id}</option>)}</select></label>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={loading} type="submit">{loading ? "Resolviendo..." : "Resolver"}</Button></div>
      </form>
    </ModalShell>
  );
}
