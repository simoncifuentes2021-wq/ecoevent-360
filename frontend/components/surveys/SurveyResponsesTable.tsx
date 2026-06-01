"use client";

import { Eye } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { mapBooleanAnswer } from "@/lib/normalizers/survey";
import type { SurveyResponse } from "@/types/survey";

function value(response: SurveyResponse, key: keyof SurveyResponse, rawKey: string) {
  return response[key] ?? response.raw_data?.[rawKey] ?? "Sin dato";
}

function text(response: SurveyResponse, key: keyof SurveyResponse, rawKey: string) {
  const item = value(response, key, rawKey);
  return typeof item === "string" || typeof item === "number" || typeof item === "boolean" ? String(item) : "Sin dato";
}

export function SurveyResponsesTable({ responses, loading, error, onView }: { responses: SurveyResponse[]; loading?: boolean; error?: string | null; onView: (response: SurveyResponse) => void }) {
  const columns: DataTableColumn<SurveyResponse>[] = [
    { key: "date", header: "Fecha", cell: (row) => row.response_date ? new Date(row.response_date).toLocaleString("es-CL") : "Sin fecha" },
    { key: "zone", header: "Zona", cell: (row) => row.zone?.name ?? text(row, "zone_id", "zona") },
    { key: "transport", header: "Transporte", cell: (row) => text(row, "transport_mode", "transporte") },
    { key: "clean", header: "Limpieza", cell: (row) => text(row, "cleanliness_rating", "limpieza") },
    { key: "bath", header: "Baños", cell: (row) => text(row, "bathroom_rating", "banos") },
    { key: "recycling", header: "Separó residuos", cell: (row) => mapBooleanAnswer(value(row, "separated_waste", "separo_residuos")) },
    { key: "rating", header: "Nota", cell: (row) => text(row, "general_rating", "nota_general") },
    { key: "comments", header: "Comentarios", cell: (row) => <span className="line-clamp-2 max-w-xs">{text(row, "comments", "comentarios")}</span> }
  ];

  return (
    <DataTable
      actions={(response) => <Button onClick={() => onView(response)} size="sm" type="button" variant="secondary"><Eye className="h-4 w-4" /></Button>}
      columns={columns}
      data={responses}
      emptyDescription="Importa un CSV desde Google Sheets para analizar respuestas."
      emptyTitle="No hay respuestas importadas todavia"
      error={error}
      getRowKey={(response, index) => response.id || String(index)}
      loading={loading}
    />
  );
}
