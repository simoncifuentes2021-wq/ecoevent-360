"use client";

import { useState } from "react";
import { FileCheck2 } from "lucide-react";
import { DisposalCertificateDefaultsSettings } from "@/components/documents/DisposalCertificateDefaultsSettings";
import { DisposalCertificateManager } from "@/components/waste/DisposalCertificateManager";

type EventOption = { id: string; name: string };

export function DisposalCertificatesDocumentSection({ events }: { events: EventOption[] }) {
  const [eventId, setEventId] = useState("");
  const selectedEvent = events.find((event) => event.id === eventId);

  return (
    <details className="group rounded-2xl border border-sky-200 bg-gradient-to-br from-white to-sky-50/50 p-4 shadow-sm sm:p-5">
      <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3">
        <span className="flex items-center gap-3">
          <span className="rounded-xl bg-sky-100 p-2.5 text-sky-800"><FileCheck2 className="h-5 w-5" /></span>
          <span><span className="block font-bold text-slate-950">Certificados de disposición final</span><span className="mt-1 block text-sm font-normal text-slate-600">Preparar y consultar certificados en un apartado independiente.</span></span>
        </span>
        <span className="text-sm font-semibold text-sky-800 group-open:hidden">Abrir apartado</span>
        <span className="hidden text-sm font-semibold text-sky-800 group-open:inline">Cerrar apartado</span>
      </summary>
      <div className="mt-4 space-y-4 border-t border-sky-100 pt-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <p className="max-w-3xl text-sm text-slate-600">La emisión usa los residuos registrados en acopios de la faena seleccionada y conserva una copia final.</p>
        <label className="grid min-w-64 gap-1.5 text-sm font-medium text-slate-700">
          Faena / evento
          <select className="h-10 rounded-lg border border-slate-300 bg-white px-3" value={eventId} onChange={(event) => setEventId(event.target.value)}>
            <option value="">Selecciona una faena</option>
            {events.map((event) => <option key={event.id} value={event.id}>{event.name}</option>)}
          </select>
        </label>
        </div>

      {selectedEvent ? (
        <DisposalCertificateManager eventId={selectedEvent.id} />
      ) : (
        <div className="rounded-xl border border-dashed border-sky-200 bg-white/80 p-5 text-center text-sm text-slate-600">
          Selecciona una faena para consultar sus materiales y preparar un certificado.
        </div>
      )}

      <DisposalCertificateDefaultsSettings />
      </div>
    </details>
  );
}
