"use client";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";

export function CloseIncidentDialog({ open, onClose, onConfirm }: { open: boolean; onClose: () => void; onConfirm: () => Promise<void> }) {
  return <ConfirmDialog open={open} title="Cerrar incidencia" description="Al cerrar la incidencia, se considera validada la solucion." onClose={onClose} onConfirm={onConfirm} />;
}
