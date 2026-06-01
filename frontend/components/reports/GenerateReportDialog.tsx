"use client";

import { FileText } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";

export function GenerateReportDialog({ open, loading, onClose, onConfirm }: { open: boolean; loading?: boolean; onClose: () => void; onConfirm: () => void }) {
  return (
    <ConfirmDialog
      confirmLabel="Generar PDF"
      description="El reporte se generara con la informacion registrada actualmente en el evento. Algunas secciones podrian aparecer como 'Sin datos registrados' si aun no tienen informacion."
      loading={loading}
      open={open}
      title="Generar reporte final"
      onClose={onClose}
      onConfirm={onConfirm}
    />
  );
}
