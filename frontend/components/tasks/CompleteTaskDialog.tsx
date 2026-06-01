"use client";

import { useState } from "react";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";

export function CompleteTaskDialog({ title = "Completar tarea", loading, onClose, onConfirm }: { title?: string; loading?: boolean; onClose: () => void; onConfirm: (observation?: string) => Promise<void> }) {
  const [observation, setObservation] = useState("");
  return (
    <ModalShell title={title} description="Puedes dejar una observacion breve para el cierre." onClose={onClose}>
      <div className="space-y-4">
        <textarea className="min-h-28 w-full rounded-2xl border px-4 py-3 text-sm outline-none focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100" value={observation} onChange={(event) => setObservation(event.target.value)} placeholder="Observacion opcional" />
        <div className="flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={loading} onClick={() => onConfirm(observation || undefined)}>{loading ? "Completando..." : "Completar"}</Button></div>
      </div>
    </ModalShell>
  );
}
