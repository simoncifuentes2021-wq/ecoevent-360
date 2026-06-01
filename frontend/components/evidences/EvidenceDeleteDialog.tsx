"use client";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import type { Evidence } from "@/types/evidence";

export function EvidenceDeleteDialog({ evidence, onClose, onConfirm }: { evidence: Evidence | null; onClose: () => void; onConfirm: () => Promise<void> }) {
  return <ConfirmDialog open={Boolean(evidence)} title="Eliminar evidencia" description="La evidencia se eliminara si el evento permite modificaciones." onClose={onClose} onConfirm={onConfirm} />;
}
