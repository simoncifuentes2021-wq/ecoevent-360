"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { Event, EventStatus } from "@/types/event";

const statuses: EventStatus[] = ["QUOTE", "PLANNING", "IN_PROGRESS", "FINISHED", "REPORT_DELIVERED", "CANCELLED"];

type StatusChangeDialogProps = {
  event: Event | null;
  loading?: boolean;
  onClose: () => void;
  onConfirm: (status: EventStatus) => Promise<void>;
};

export function StatusChangeDialog({ event, loading, onClose, onConfirm }: StatusChangeDialogProps) {
  const [status, setStatus] = useState<EventStatus>("PLANNING");

  if (!event) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl">
        <h2 className="text-xl font-bold text-slate-950">Cambiar estado</h2>
        <p className="mt-2 text-sm text-slate-600">Actualiza el estado operacional de {event.name}.</p>
        <select
          className="mt-5 h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 text-sm outline-none focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
          onChange={(item) => setStatus(item.target.value as EventStatus)}
          value={status}
        >
          {statuses.map((item) => (
            <option key={item} value={item}>
              {item.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <div className="mt-6 flex justify-end gap-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={loading} type="button" onClick={() => onConfirm(status)}>
            {loading ? "Actualizando..." : "Cambiar estado"}
          </Button>
        </div>
      </div>
    </div>
  );
}
