"use client";

import { ExternalLink } from "lucide-react";

import { ModalShell } from "@/components/common/ModalShell";
import { SurveyStatusBadge } from "@/components/surveys/SurveyStatusBadge";
import { Button } from "@/components/ui/button";
import type { Survey } from "@/types/survey";

export function SurveyDetailDrawer({ survey, onClose }: { survey: Survey | null; onClose: () => void }) {
  if (!survey) return null;
  return (
    <ModalShell title={survey.title} description="Configuracion de encuesta externa y enlaces asociados." onClose={onClose}>
      <div className="space-y-4 text-sm">
        <SurveyStatusBadge status={survey.status} />
        <p className="text-slate-600">{survey.description || "Sin descripcion."}</p>
        {survey.google_form_url ? <Button onClick={() => window.open(survey.google_form_url || "", "_blank")} type="button" variant="secondary"><ExternalLink className="h-4 w-4" />Abrir Google Form</Button> : null}
        {survey.google_sheet_url ? <Button onClick={() => window.open(survey.google_sheet_url || "", "_blank")} type="button" variant="secondary"><ExternalLink className="h-4 w-4" />Abrir Google Sheet</Button> : null}
        <div className="grid gap-2 rounded-xl bg-slate-50 p-3">
          <span>Apertura: {survey.opens_at ? new Date(survey.opens_at).toLocaleString("es-CL") : "Sin fecha"}</span>
          <span>Cierre: {survey.closes_at ? new Date(survey.closes_at).toLocaleString("es-CL") : "Sin fecha"}</span>
          <span>Respuestas: {survey.responses_count ?? "No informado"}</span>
        </div>
      </div>
    </ModalShell>
  );
}
