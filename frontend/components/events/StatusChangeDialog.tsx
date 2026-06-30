"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { eventStatusLabels } from "@/lib/status-labels";
import type { Event, EventStatus } from "@/types/event";

const validTransitions: Record<EventStatus, EventStatus[]> = {
  QUOTE: ["PLANNING", "CANCELLED"],
  PLANNING: ["IN_PROGRESS", "FINISHED", "CANCELLED"],
  IN_PROGRESS: ["FINISHED", "CANCELLED"],
  FINISHED: ["REPORT_DELIVERED"],
  REPORT_DELIVERED: [],
  CANCELLED: []
};

type StatusChangeDialogProps = {
  event: Event | null;
  loading?: boolean;
  onClose: () => void;
  onConfirm: (status: EventStatus) => Promise<void>;
};

export function StatusChangeDialog({ event, loading, onClose, onConfirm }: StatusChangeDialogProps) {
  const [status, setStatus] = useState<EventStatus>("PLANNING");
  const options = useMemo(() => {
    if (!event) return [];
    return validTransitions[event.status];
  }, [event]);

  useEffect(() => {
    if (options[0]) setStatus(options[0]);
  }, [options]);

  if (!event) return null;
  const hasOptions = options.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl">
        <h2 className="text-xl font-bold text-slate-950">Cambiar estado</h2>
        <p className="mt-2 text-sm text-slate-600">
          Estado actual: <span className="font-semibold">{eventStatusLabels[event.status]}</span>
        </p>
        {hasOptions ? (
          <select
            className="mt-5 h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 text-sm outline-none focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
            onChange={(item) => setStatus(item.target.value as EventStatus)}
            value={status}
          >
            {options.map((item) => (
              <option key={item} value={item}>
                {eventStatusLabels[item]}
              </option>
            ))}
          </select>
        ) : (
          <div className="mt-5 rounded-2xl bg-amber-50 p-4 text-sm font-semibold text-amber-800">
            Este evento no tiene cambios de estado disponibles desde su estado actual.
          </div>
        )}
        <div className="mt-6 flex justify-end gap-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={loading || !hasOptions} type="button" onClick={() => onConfirm(status)}>
            {loading ? "Actualizando..." : "Cambiar estado"}
          </Button>
        </div>
      </div>
    </div>
  );
}
