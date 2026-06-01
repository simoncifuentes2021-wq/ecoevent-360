"use client";

import { useState } from "react";
import { FileSpreadsheet, Upload } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { Button } from "@/components/ui/button";
import { importSurveyResponsesCsv } from "@/lib/api/surveyResponses";
import { normalizeImportResult } from "@/lib/normalizers/survey";
import type { CSVImportResult, Survey } from "@/types/survey";

export function CSVImportUploader({ survey, onImported }: { survey: Survey; onImported: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CSVImportResult | null>(null);

  async function submit() {
    if (!file) {
      setError("El archivo debe ser CSV.");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".csv") && file.type !== "text/csv") {
      setError("El archivo debe ser CSV.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await importSurveyResponsesCsv(survey.id, file);
      setResult(normalizeImportResult(response));
      onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo importar el CSV.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><FileSpreadsheet className="h-5 w-5" /></span>
        <div>
          <h3 className="font-bold text-slate-950">Importar respuestas CSV</h3>
          <p className="text-sm text-slate-600">Desde Google Sheets: Archivo &gt; Descargar &gt; Valores separados por comas (.csv).</p>
        </div>
      </div>
      {error ? <ErrorState message={error} title="No se pudo importar" /> : null}
      <input accept=".csv,text/csv" className="block w-full rounded-xl border border-dashed border-slate-300 p-4 text-sm" onChange={(event) => setFile(event.target.files?.[0] ?? null)} type="file" />
      {file ? <p className="text-sm text-slate-600">{file.name} · {(file.size / 1024).toFixed(1)} KB</p> : null}
      <Button disabled={loading || !file} onClick={submit} type="button"><Upload className="h-4 w-4" />{loading ? "Importando..." : "Importar CSV"}</Button>
      {result ? (
        <div className="grid gap-2 rounded-xl bg-slate-50 p-3 text-sm sm:grid-cols-3">
          <span>Importadas: <strong>{result.imported_rows ?? 0}</strong></span>
          <span>Omitidas: <strong>{result.skipped_rows ?? 0}</strong></span>
          <span>Duplicadas: <strong>{result.duplicated_rows ?? 0}</strong></span>
          {result.message ? <span className="sm:col-span-3">{result.message}</span> : null}
        </div>
      ) : null}
    </div>
  );
}
