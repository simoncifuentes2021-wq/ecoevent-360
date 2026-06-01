"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { CSVImportUploader } from "@/components/surveys/CSVImportUploader";
import { CloseSurveyDialog } from "@/components/surveys/CloseSurveyDialog";
import { SurveyCharts } from "@/components/surveys/SurveyCharts";
import { SurveyDetailDrawer } from "@/components/surveys/SurveyDetailDrawer";
import { SurveyFilters } from "@/components/surveys/SurveyFilters";
import { SurveyFormModal } from "@/components/surveys/SurveyFormModal";
import { SurveyResponseDetailModal } from "@/components/surveys/SurveyResponseDetailModal";
import { SurveyResponsesTable } from "@/components/surveys/SurveyResponsesTable";
import { SurveySummaryCards } from "@/components/surveys/SurveySummaryCards";
import { SurveyTable } from "@/components/surveys/SurveyTable";
import { SurveyQrTab } from "@/components/qr/SurveyQrTab";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { closeSurvey, createSurvey, getEventSurveys, updateSurvey } from "@/lib/api/surveys";
import { getSurveyResponses, getSurveySummary } from "@/lib/api/surveyResponses";
import { getEventZones } from "@/lib/api/zones";
import { normalizeSurveySummary } from "@/lib/normalizers/survey";
import { canCloseSurvey, canCreateSurvey, canEditSurvey, canImportSurveyCsv, canManageSurveyQr, canViewSurveyResponses, canViewSurveySummary } from "@/lib/permissions";
import type { UserRole } from "@/types/roles";
import type { Survey, SurveyCreate, SurveyResponse, SurveySummary } from "@/types/survey";
import type { Zone } from "@/types/zone";

export function SurveysTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [responses, setResponses] = useState<SurveyResponse[]>([]);
  const [summary, setSummary] = useState<SurveySummary>(normalizeSurveySummary(null));
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [formSurvey, setFormSurvey] = useState<Survey | null | undefined>();
  const [selected, setSelected] = useState<Survey | null>(null);
  const [detail, setDetail] = useState<Survey | null>(null);
  const [importSurvey, setImportSurvey] = useState<Survey | null>(null);
  const [closing, setClosing] = useState<Survey | null>(null);
  const [responseDetail, setResponseDetail] = useState<SurveyResponse | null>(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [surveyData, zoneData] = await Promise.all([
        getEventSurveys(eventId),
        getEventZones(eventId).catch(() => [])
      ]);
      setSurveys(surveyData.items);
      setZones(zoneData);
      if (!selected && surveyData.items[0]) setSelected(surveyData.items[0]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar las encuestas.");
    } finally {
      setLoading(false);
    }
  }, [eventId, selected]);

  const loadSelected = useCallback(async (survey: Survey | null) => {
    if (!survey) {
      setResponses([]);
      setSummary(normalizeSurveySummary(null));
      return;
    }
    setDetailLoading(true);
    setDetailError(null);
    const [responsesData, summaryData] = await Promise.allSettled([
      canViewSurveyResponses(role) ? getSurveyResponses(survey.id) : Promise.resolve({ items: [], total: 0, page: 1, limit: 0 }),
      canViewSurveySummary(role) ? getSurveySummary(survey.id) : Promise.resolve(null)
    ]);
    if (responsesData.status === "fulfilled") setResponses(responsesData.value.items);
    if (summaryData.status === "fulfilled") setSummary(normalizeSurveySummary(summaryData.value));
    const rejected = [responsesData, summaryData].find((item) => item.status === "rejected");
    if (rejected?.status === "rejected") setDetailError(rejected.reason instanceof Error ? rejected.reason.message : "No se pudo cargar el resumen de encuesta.");
    setDetailLoading(false);
  }, [role]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void loadSelected(selected); }, [loadSelected, selected]);

  const filtered = useMemo(() => surveys.filter((survey) => {
    const text = `${survey.title} ${survey.description ?? ""}`.toLowerCase();
    return (!q || text.includes(q.toLowerCase())) && (!status || survey.status === status);
  }), [q, status, surveys]);

  async function save(data: SurveyCreate) {
    setSaving(true);
    try {
      const saved = formSurvey ? await updateSurvey(formSurvey.id, data) : await createSurvey(eventId, data);
      setFormSurvey(undefined);
      setSelected(saved);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function confirmClose() {
    if (!closing) return;
    setSaving(true);
    try {
      const closed = await closeSurvey(closing.id);
      setClosing(null);
      setSelected(closed);
      await load();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-950">Encuestas y experiencia de asistentes</h2>
          <p className="text-sm text-slate-600">Gestiona Google Forms, importa CSV desde Sheets y analiza satisfaccion por evento.</p>
        </div>
        {canCreateSurvey(role) ? <Button onClick={() => setFormSurvey(null)} type="button"><Plus className="h-4 w-4" />Crear encuesta</Button> : null}
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <SurveyFilters q={q} status={status} onQChange={setQ} onStatusChange={setStatus} />
      <SurveyTable
        canManage={canEditSurvey(role)}
        error={null}
        loading={loading}
        surveys={filtered}
        onCloseSurvey={(survey) => canCloseSurvey(role) && setClosing(survey)}
        onEdit={setFormSurvey}
        onImport={(survey) => canImportSurveyCsv(role) && setImportSurvey(survey)}
        onSelect={(survey) => { setSelected(survey); setDetail(survey); }}
      />
      {selected ? (
        <div className="space-y-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h3 className="font-bold text-slate-950">Analisis: {selected.title}</h3>
                  <p className="text-sm text-slate-600">Resumen de respuestas importadas y percepcion del publico.</p>
                </div>
                {selected.google_form_url ? <Button onClick={() => window.open(selected.google_form_url || "", "_blank")} type="button" variant="secondary">Abrir formulario</Button> : null}
              </div>
            </CardContent>
          </Card>
          {detailError ? <ErrorState message={detailError} title="Datos parciales" /> : null}
          {canViewSurveySummary(role) ? <SurveySummaryCards summary={summary} /> : null}
          {canViewSurveySummary(role) ? <SurveyCharts summary={summary} /> : null}
          {canImportSurveyCsv(role) ? <CSVImportUploader survey={selected} onImported={() => loadSelected(selected)} /> : null}
          {canManageSurveyQr(role) ? <SurveyQrTab canManage={canManageSurveyQr(role)} survey={selected} zones={zones} /> : null}
          {canViewSurveyResponses(role) ? <SurveyResponsesTable error={null} loading={detailLoading} responses={responses} onView={setResponseDetail} /> : null}
        </div>
      ) : !loading ? (
        <EmptyState title="Selecciona o crea una encuesta" description="Cuando exista una encuesta, aqui veras el resumen, respuestas y QR." />
      ) : null}
      {formSurvey !== undefined ? <SurveyFormModal loading={saving} survey={formSurvey} onClose={() => setFormSurvey(undefined)} onSubmit={save} /> : null}
      <CloseSurveyDialog loading={saving} survey={closing} onClose={() => setClosing(null)} onConfirm={confirmClose} />
      <SurveyDetailDrawer survey={detail} onClose={() => setDetail(null)} />
      <SurveyResponseDetailModal response={responseDetail} onClose={() => setResponseDetail(null)} />
      {importSurvey ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4">
          <div className="w-full max-w-xl rounded-3xl bg-white p-5 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div><h3 className="text-lg font-bold">Importar CSV</h3><p className="text-sm text-slate-600">{importSurvey.title}</p></div>
              <button className="rounded-full px-3 py-1 text-xl text-slate-400 hover:bg-slate-100" onClick={() => setImportSurvey(null)} type="button">x</button>
            </div>
            <CSVImportUploader survey={importSurvey} onImported={() => { setImportSurvey(null); void loadSelected(importSurvey); }} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
