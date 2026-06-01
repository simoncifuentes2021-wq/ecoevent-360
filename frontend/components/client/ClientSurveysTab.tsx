"use client";

import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { SurveyCharts } from "@/components/surveys/SurveyCharts";
import { SurveyStatusBadge } from "@/components/surveys/SurveyStatusBadge";
import { SurveySummaryCards } from "@/components/surveys/SurveySummaryCards";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getEventSurveys } from "@/lib/api/surveys";
import { getSurveySummary } from "@/lib/api/surveyResponses";
import { normalizeSurveySummary } from "@/lib/normalizers/survey";
import type { Survey, SurveySummary } from "@/types/survey";

export function ClientSurveysTab({ eventId }: { eventId: string }) {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [selected, setSelected] = useState<Survey | null>(null);
  const [summary, setSummary] = useState<SurveySummary>(normalizeSurveySummary(null));
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getEventSurveys(eventId);
        setSurveys(data.items);
        setSelected(data.items[0] ?? null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudieron cargar las encuestas.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [eventId]);

  useEffect(() => {
    async function loadSummary() {
      if (!selected) {
        setSummary(normalizeSurveySummary(null));
        return;
      }
      setSummaryLoading(true);
      try {
        setSummary(normalizeSurveySummary(await getSurveySummary(selected.id)));
      } catch {
        setSummary(normalizeSurveySummary(null));
      } finally {
        setSummaryLoading(false);
      }
    }
    void loadSummary();
  }, [selected]);

  if (loading) return <LoadingState label="Cargando encuestas..." />;
  if (error) return <ErrorState message={error} />;
  if (!surveys.length) return <Card><CardContent className="p-6 text-sm text-slate-600">Aun no hay encuestas disponibles para este evento.</CardContent></Card>;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {surveys.map((survey) => (
          <button className={`rounded-2xl border p-4 text-left transition ${selected?.id === survey.id ? "border-emerald-500 bg-emerald-50" : "border-slate-200 bg-white hover:border-emerald-200"}`} key={survey.id} onClick={() => setSelected(survey)} type="button">
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-bold text-slate-950">{survey.title}</h3>
              <SurveyStatusBadge status={survey.status} />
            </div>
            <p className="mt-2 text-sm text-slate-600">{survey.description || "Encuesta de experiencia del evento."}</p>
            {survey.status === "ACTIVE" && survey.google_form_url ? <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-emerald-700"><ExternalLink className="h-4 w-4" />Formulario activo</span> : null}
          </button>
        ))}
      </div>
      {selected?.google_form_url && selected.status === "ACTIVE" ? <Button onClick={() => window.open(selected.google_form_url || "", "_blank")} type="button" variant="secondary"><ExternalLink className="h-4 w-4" />Abrir formulario</Button> : null}
      {summaryLoading ? <LoadingState label="Cargando resumen..." /> : <><SurveySummaryCards summary={summary} /><SurveyCharts summary={summary} /></>}
    </div>
  );
}
