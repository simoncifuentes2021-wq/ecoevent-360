"use client";

import { ExternalLink, Eye, FileSpreadsheet, Lock, Pencil, Upload } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { SurveyStatusBadge } from "@/components/surveys/SurveyStatusBadge";
import { Button } from "@/components/ui/button";
import type { Survey } from "@/types/survey";

export function SurveyTable({
  surveys,
  loading,
  error,
  canManage,
  onEdit,
  onCloseSurvey,
  onSelect,
  onImport
}: {
  surveys: Survey[];
  loading?: boolean;
  error?: string | null;
  canManage?: boolean;
  onEdit: (survey: Survey) => void;
  onCloseSurvey: (survey: Survey) => void;
  onSelect: (survey: Survey) => void;
  onImport: (survey: Survey) => void;
}) {
  const columns: DataTableColumn<Survey>[] = [
    { key: "title", header: "Encuesta", cell: (survey) => <div><p className="font-semibold text-slate-950">{survey.title}</p><p className="text-xs text-slate-500">{survey.description || "Sin descripcion"}</p></div> },
    { key: "status", header: "Estado", cell: (survey) => <SurveyStatusBadge status={survey.status} /> },
    { key: "form", header: "Google Form", cell: (survey) => survey.google_form_url ? <a className="inline-flex items-center gap-1 text-emerald-700 hover:underline" href={survey.google_form_url} rel="noreferrer" target="_blank"><ExternalLink className="h-3.5 w-3.5" />Abrir</a> : "Sin enlace" },
    { key: "sheet", header: "Sheet", cell: (survey) => survey.google_sheet_url ? <a className="inline-flex items-center gap-1 text-sky-700 hover:underline" href={survey.google_sheet_url} rel="noreferrer" target="_blank"><FileSpreadsheet className="h-3.5 w-3.5" />Sheet</a> : "Opcional" },
    { key: "responses", header: "Respuestas", cell: (survey) => survey.responses_count ?? "Sin importar" }
  ];

  return (
    <DataTable
      actions={(survey) => (
        <div className="flex justify-end gap-2">
          <Button onClick={() => onSelect(survey)} size="sm" type="button" variant="secondary"><Eye className="h-4 w-4" /></Button>
          {canManage ? <Button onClick={() => onImport(survey)} size="sm" type="button" variant="secondary"><Upload className="h-4 w-4" /></Button> : null}
          {canManage ? <Button onClick={() => onEdit(survey)} size="sm" type="button" variant="secondary"><Pencil className="h-4 w-4" /></Button> : null}
          {canManage && survey.status !== "CLOSED" ? <Button onClick={() => onCloseSurvey(survey)} size="sm" type="button" variant="secondary"><Lock className="h-4 w-4" /></Button> : null}
        </div>
      )}
      columns={columns}
      data={surveys}
      emptyDescription="Crea una encuesta externa de Google Forms y luego importa sus respuestas CSV."
      emptyTitle="No hay encuestas para este evento"
      error={error}
      getRowKey={(survey) => survey.id}
      loading={loading}
    />
  );
}
