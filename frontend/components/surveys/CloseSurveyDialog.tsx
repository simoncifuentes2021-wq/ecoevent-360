"use client";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import type { Survey } from "@/types/survey";

export function CloseSurveyDialog({ survey, loading, onClose, onConfirm }: { survey: Survey | null; loading?: boolean; onClose: () => void; onConfirm: () => void }) {
  return (
    <ConfirmDialog
      confirmLabel="Cerrar encuesta"
      description="Al cerrar la encuesta, se bloqueara su edicion operativa y quedara lista para analisis."
      loading={loading}
      open={Boolean(survey)}
      title={`Cerrar ${survey?.title ?? "encuesta"}`}
      onClose={onClose}
      onConfirm={onConfirm}
    />
  );
}
