"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { AlertTriangle, Info, ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";

type Tone = "normal" | "warning" | "danger";

const toneStyles: Record<Tone, string> = {
  normal: "bg-emerald-50 text-emerald-700",
  warning: "bg-amber-50 text-amber-700",
  danger: "bg-rose-50 text-rose-700",
};

export function LogbookDialog({
  open,
  title,
  description,
  children,
  confirmLabel,
  cancelLabel = "Volver",
  tone = "normal",
  busy = false,
  error,
  confirmDisabled = false,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  description: string;
  children?: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: Tone;
  busy?: boolean;
  error?: string;
  confirmDisabled?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  const errorId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  if (!open) return null;
  const Icon = tone === "danger" ? ShieldAlert : tone === "warning" ? AlertTriangle : Info;

  return (
    <dialog
      aria-describedby={`${descriptionId}${error ? ` ${errorId}` : ""}`}
      aria-labelledby={titleId}
      className="m-auto max-h-[92dvh] w-[calc(100%-1.5rem)] max-w-lg overflow-y-auto rounded-3xl border-0 bg-white p-0 shadow-2xl backdrop:bg-slate-950/50"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      ref={dialogRef}
    >
      <div className="p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-2xl ${toneStyles[tone]}`}>
            <Icon aria-hidden="true" className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-xl font-bold text-slate-950" id={titleId}>{title}</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600" id={descriptionId}>{description}</p>
          </div>
        </div>
        {children ? <div className="mt-5">{children}</div> : null}
        {error ? (
          <p className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800" id={errorId} role="alert">
            {error}
          </p>
        ) : null}
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button className="min-h-11" disabled={busy} onClick={onClose} type="button" variant="secondary">
            {cancelLabel}
          </Button>
          <Button
            className={`min-h-11 ${tone === "danger" ? "bg-rose-700 text-white hover:bg-rose-800" : ""}`}
            disabled={busy || confirmDisabled}
            onClick={onConfirm}
            type="button"
            variant="primary"
          >
            {busy ? "Procesando…" : confirmLabel}
          </Button>
        </div>
      </div>
    </dialog>
  );
}
