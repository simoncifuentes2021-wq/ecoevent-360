"use client";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import type { Report } from "@/types/report";

export function MarkReportDeliveredDialog({ report, loading, onClose, onConfirm }: { report: Report | null; loading?: boolean; onClose: () => void; onConfirm: () => void }) {
  return (
    <ConfirmDialog
      confirmLabel="Marcar entregado"
      description="Al marcar como entregado, quedara registrado como informe enviado al cliente."
      loading={loading}
      open={Boolean(report)}
      title={`Entregar ${report?.title ?? "reporte"}`}
      onClose={onClose}
      onConfirm={onConfirm}
    />
  );
}
