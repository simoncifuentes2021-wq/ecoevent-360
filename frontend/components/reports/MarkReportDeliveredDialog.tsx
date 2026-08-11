"use client";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import type { Report } from "@/types/report";

export function MarkReportDeliveredDialog({ report, loading, onClose, onConfirm }: { report: Report | null; loading?: boolean; onClose: () => void; onConfirm: () => void }) {
  return (
    <ConfirmDialog
      confirmLabel="Generar y entregar PDF"
      description="Se usará la última versión PDF premium. Si todavía no existe, se generará, guardará en Cloudflare y quedará disponible para el cliente."
      loading={loading}
      open={Boolean(report)}
      title={`Entregar ${report?.title ?? "reporte"}`}
      onClose={onClose}
      onConfirm={onConfirm}
    />
  );
}
