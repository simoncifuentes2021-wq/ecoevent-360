"use client";

import { ModalShell } from "@/components/common/ModalShell";
import type { SurveyResponse } from "@/types/survey";

export function SurveyResponseDetailModal({ response, onClose }: { response: SurveyResponse | null; onClose: () => void }) {
  if (!response) return null;
  const entries = Object.entries(response.raw_data ?? {}).slice(0, 30);
  return (
    <ModalShell title="Detalle de respuesta" description="Datos anonimizados importados desde CSV." onClose={onClose}>
      <div className="space-y-3">
        <p className="text-sm text-slate-600">Fecha: {response.response_date ? new Date(response.response_date).toLocaleString("es-CL") : "Sin fecha"}</p>
        <p className="text-sm text-slate-600">Comentarios: {response.comments || "Sin comentarios"}</p>
        <div className="rounded-xl bg-slate-50 p-3">
          <h3 className="mb-2 text-sm font-semibold">Datos originales</h3>
          {entries.length ? entries.map(([key, value]) => <div className="grid grid-cols-[.8fr_1.2fr] gap-2 border-b py-2 text-sm last:border-0" key={key}><span className="font-medium text-slate-700">{key}</span><span className="text-slate-600">{String(value)}</span></div>) : <p className="text-sm text-slate-500">No hay raw_data disponible.</p>}
        </div>
      </div>
    </ModalShell>
  );
}
