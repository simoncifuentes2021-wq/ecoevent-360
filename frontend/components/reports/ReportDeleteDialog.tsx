"use client";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import type { Report } from "@/types/report";

export function ReportDeleteDialog({ report, loading, onClose, onConfirm }: { report: Report | null; loading?: boolean; onClose: () => void; onConfirm: () => void }) {
  const delivered = report?.status === "DELIVERED";
  return (
    <ConfirmDialog
      confirmLabel={delivered ? "Anular reporte entregado" : "Anular reporte"}
      description={delivered ? "Este reporte ya fue entregado. Se recomienda versionar en vez de eliminar. Confirma solo si corresponde anularlo." : "Esta accion dejara de mostrar el reporte en el listado disponible para el evento."}
      loading={loading}
      open={Boolean(report)}
      title={`Anular ${report?.title ?? "reporte"}`}
      onClose={onClose}
      onConfirm={onConfirm}
    />
  );
}
