"use client";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import type { WasteRecord } from "@/types/waste";

export function WasteDeleteDialog({ record, onClose, onConfirm }: { record: WasteRecord | null; onClose: () => void; onConfirm: () => Promise<void> }) {
  return <ConfirmDialog open={Boolean(record)} title="Eliminar registro de residuo" description="Esta accion puede afectar los indicadores ambientales del evento. Confirma solo si el registro fue ingresado por error." onClose={onClose} onConfirm={onConfirm} />;
}
