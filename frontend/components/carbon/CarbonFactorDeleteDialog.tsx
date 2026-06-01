"use client";
import { ConfirmDialog } from "@/components/common/ConfirmDialog"; import type { CarbonFactor } from "@/types/carbon";
export function CarbonFactorDeleteDialog({ factor, onClose, onConfirm }: { factor: CarbonFactor | null; onClose: () => void; onConfirm: () => Promise<void> }) { return <ConfirmDialog open={Boolean(factor)} title="Eliminar factor" description="El factor se eliminara o desactivara si el backend lo permite." onClose={onClose} onConfirm={onConfirm} />; }
