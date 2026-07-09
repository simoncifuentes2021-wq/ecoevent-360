"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, QrCode } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { FormQrDialog } from "@/components/event-forms/FormQrDialog";
import { Button } from "@/components/ui/button";
import { getEventForms, getEventFormSummary } from "@/lib/api/eventForms";
import type { EventForm, EventFormSummary } from "@/types/eventForm";

export function ClientFormsTab({ eventId }: { eventId: string }) {
  const [forms, setForms] = useState<EventForm[]>([]);
  const [summaries, setSummaries] = useState<Record<string, EventFormSummary>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [qrForm, setQrForm] = useState<EventForm | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getEventForms(eventId);
      setForms(data.items);
      const pairs = await Promise.all(data.items.map(async (form) => [form.id, await getEventFormSummary(form.id)] as const).map((promise) => promise.catch(() => null)));
      setSummaries(Object.fromEntries(pairs.filter(Boolean) as Array<[string, EventFormSummary]>));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar los formularios.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <LoadingState label="Cargando formularios..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!forms.length) return <p className="rounded-lg border bg-white p-5 text-sm text-slate-600">Aún no hay formularios propios disponibles.</p>;

  return (
    <>
      <div className="grid gap-3 md:grid-cols-2">
        {forms.map((form) => {
          const summary = summaries[form.id];
          return (
            <article className="rounded-lg border bg-white p-4 shadow-sm" key={form.id}>
              <h3 className="font-bold text-slate-950">{form.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{summary?.total_responses ?? 0} respuestas registradas</p>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                <span className="rounded-md bg-slate-50 p-2">Activos<br /><strong>{form.status}</strong></span>
                <span className="rounded-md bg-slate-50 p-2">Idiomas<br /><strong>{form.available_languages.join(", ")}</strong></span>
                <span className="rounded-md bg-slate-50 p-2">Bike Zone<br /><strong>{summary?.bike_zone_total ?? 0}</strong></span>
              </div>
              {form.status === "ACTIVE" ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button type="button" variant="secondary" onClick={() => window.open(`/f/${form.public_slug}`, "_blank")}><ExternalLink className="h-4 w-4" />Abrir formulario</Button>
                  <Button type="button" variant="secondary" onClick={() => setQrForm(form)}><QrCode className="h-4 w-4" />QR</Button>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
      {qrForm ? <FormQrDialog canCreate={false} canDelete={false} form={qrForm} onClose={() => setQrForm(null)} /> : null}
    </>
  );
}
