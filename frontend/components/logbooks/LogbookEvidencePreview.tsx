"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ImageIcon, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getLogbookEvidenceAccess } from "@/lib/api/logbooks";
import { API_ORIGIN } from "@/lib/constants";
import { logbookError } from "@/lib/logbook-errors";
import type { LogbookEvidence } from "@/types/logbook";

export function LogbookEvidencePreview({
  evidence,
  onClose,
}: {
  evidence: LogbookEvidence | null;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const dialog = dialogRef.current;
    if (evidence && dialog && !dialog.open) dialog.showModal();
    if (!evidence && dialog?.open) dialog.close();
  }, [evidence]);

  useEffect(() => {
    if (!evidence) {
      setUrl("");
      setError("");
      return;
    }
    let active = true;
    setLoading(true);
    setError("");
    getLogbookEvidenceAccess(evidence.id)
      .then((access) => {
        if (active) setUrl(`${API_ORIGIN}${access.url}`);
      })
      .catch((reason) => {
        if (active) setError(logbookError(reason, "No se pudo cargar la fotografía."));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [evidence]);

  if (!evidence) return null;

  return (
    <dialog
      aria-describedby={descriptionId}
      aria-labelledby={titleId}
      className="m-auto max-h-[94dvh] w-[calc(100%-1rem)] max-w-4xl overflow-hidden rounded-3xl border-0 bg-white p-0 shadow-2xl backdrop:bg-slate-950/70"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      ref={dialogRef}
    >
      <div className="flex max-h-[94dvh] flex-col">
        <header className="flex items-start justify-between gap-3 border-b p-4 sm:p-5">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-bold" id={titleId}>{evidence.original_filename}</h2>
            <p className="text-sm text-slate-500" id={descriptionId}>
              Evidencia fotográfica · {Math.max(1, Math.round(evidence.file_size / 1024))} KB
            </p>
          </div>
          <button aria-label="Cerrar fotografía" className="grid h-11 w-11 shrink-0 place-items-center rounded-full hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-600" onClick={onClose} type="button">
            <X aria-hidden="true" className="h-5 w-5" />
          </button>
        </header>
        <div className="grid min-h-64 flex-1 place-items-center overflow-auto bg-slate-950 p-2 sm:p-4">
          {loading ? <p className="text-sm text-white">Cargando fotografía…</p> : null}
          {error ? <div className="max-w-md rounded-2xl bg-white p-5 text-center"><ImageIcon className="mx-auto h-8 w-8 text-rose-600"/><p className="mt-2 text-sm text-rose-700" role="alert">{error}</p><Button className="mt-4" onClick={onClose} variant="secondary">Cerrar</Button></div> : null}
          {url && !error ? (
            // The signed URL is short-lived and is never persisted in application state.
            // eslint-disable-next-line @next/next/no-img-element
            <img alt={`Evidencia ${evidence.original_filename}`} className="max-h-[72dvh] max-w-full object-contain" onError={() => setError("La fotografía no pudo mostrarse. Vuelve a intentarlo.")} src={url}/>
          ) : null}
        </div>
        {evidence.comment ? <p className="border-t p-4 text-sm text-slate-700">{evidence.comment}</p> : null}
      </div>
    </dialog>
  );
}
