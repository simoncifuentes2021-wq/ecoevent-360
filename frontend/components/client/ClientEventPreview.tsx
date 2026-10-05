"use client";

import { useEffect } from "react";
import { Eye, X } from "lucide-react";

import { ClientAccessNotice } from "@/components/client/ClientAccessNotice";
import { ClientEventHeader } from "@/components/client/ClientEventHeader";
import { ClientEventLogisticsCard } from "@/components/client/ClientEventLogisticsCard";
import { ClientEventTabs } from "@/components/client/ClientEventTabs";
import { Card, CardContent } from "@/components/ui/card";
import type { ClientPortal } from "@/types/clientPortal";
import type { Event } from "@/types/event";

export function ClientEventPreview({ event, portal, onClose }: { event: Event; portal: ClientPortal; onClose: () => void }) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(keyEvent: KeyboardEvent) {
      if (keyEvent.key === "Escape") onClose();
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <div
      aria-label="Vista previa del portal cliente"
      aria-modal="true"
      className="fixed inset-0 z-[80] bg-slate-950/70 p-2 backdrop-blur-sm sm:p-4"
      onMouseDown={(mouseEvent) => { if (mouseEvent.target === mouseEvent.currentTarget) onClose(); }}
      role="dialog"
    >
      <div className="mx-auto flex h-full max-w-[1600px] flex-col overflow-hidden rounded-2xl border border-slate-700/70 bg-slate-100 shadow-2xl" onMouseDown={(mouseEvent) => mouseEvent.stopPropagation()}>
        <header className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-indigo-100 text-indigo-700"><Eye className="h-5 w-5" /></span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-bold text-slate-950">Vista previa del Portal cliente</p>
                <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-indigo-700">Solo lectura</span>
              </div>
              <p className="truncate text-sm text-slate-500">Así verá el cliente: {event.name}</p>
            </div>
          </div>
          <button aria-label="Cerrar vista previa" className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-indigo-500/30" onClick={onClose} type="button">
            <X className="h-5 w-5" />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="space-y-6 p-3 sm:p-6">
            <div className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3 text-indigo-950 sm:px-5">
              <p className="text-sm font-bold">Vista previa interactiva del portal cliente</p>
              <p className="mt-1 text-sm text-indigo-800">Puedes navegar por las secciones habilitadas sin abandonar la configuración del evento. Las acciones se mantienen en modo solo lectura.</p>
            </div>
            <ClientEventHeader event={event} showBack={false} />
            <ClientEventLogisticsCard event={event} />
            <ClientAccessNotice />
            <ClientEventTabs eventId={event.id} portalOverride={portal} />
            <Card className="border-dashed bg-white/70">
              <CardContent className="p-4 text-xs text-slate-500">Presiona Esc, haz clic fuera de la ventana o usa el botón cerrar para volver a la configuración del Portal cliente.</CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
