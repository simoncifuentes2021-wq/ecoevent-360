"use client";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirmar",
  loading,
  onConfirm,
  onClose
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  loading?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/45 p-4">
      <div className="w-full max-w-md rounded-lg border bg-white p-5 shadow-soft">
        <div className="flex gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-amber-50 text-amber-700">
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-lg font-bold">{title}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{description}</p>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button disabled={loading} onClick={onClose} type="button" variant="secondary">
            Cancelar
          </Button>
          <Button disabled={loading} onClick={onConfirm} type="button">
            {loading ? "Procesando..." : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
