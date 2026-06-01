"use client";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import type { CarbonRecord } from "@/types/carbon";

export function CarbonDeleteDialog({ record, onClose, onConfirm }: { record: CarbonRecord | null; onClose: () => void; onConfirm: () => Promise<void> }) {
  return <ConfirmDialog open={Boolean(record)} title="Eliminar registro de carbono" description="Esta accion puede afectar los indicadores de huella del evento." onClose={onClose} onConfirm={onConfirm} />;
}
