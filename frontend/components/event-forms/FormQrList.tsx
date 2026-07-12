"use client";

import { useEffect, useState } from "react";
import { Download, Trash2 } from "lucide-react";

import { CopyPublicLinkButton } from "@/components/event-forms/CopyPublicLinkButton";
import { Button } from "@/components/ui/button";
import { downloadFormQrCode, getFormQrBlob } from "@/lib/api/formQr";
import type { FormQrCode } from "@/types/formQr";

export function FormQrList({ items, canDelete, onDelete }: { items: FormQrCode[]; canDelete: boolean; onDelete: (qr: FormQrCode) => void }) {
  if (!items.length) return <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">Todavia no hay QR generados para este formulario.</p>;
  return (
    <div className="grid gap-3">
      {items.map((qr) => (
        <article className="rounded-lg border bg-white p-3" key={qr.id}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 flex-1 flex-wrap gap-3">
              <QrPreview qr={qr} />
              <div className="min-w-0 flex-1">
                <p className="font-bold text-slate-950">{qr.label}</p>
                <p className="text-xs font-semibold text-slate-500">{qr.qr_type}{qr.language ? ` - ${qr.language}` : ""}</p>
                <p className="mt-1 break-all text-xs text-emerald-700">{qr.target_url}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <CopyPublicLinkButton label="Copiar" url={qr.target_url} />
              <Button size="sm" type="button" variant="secondary" onClick={() => downloadFormQrCode(qr)}>
                <Download className="h-4 w-4" />
                PNG
              </Button>
              {canDelete ? (
                <Button size="sm" type="button" variant="secondary" onClick={() => onDelete(qr)}>
                  <Trash2 className="h-4 w-4" />
                  Eliminar
                </Button>
              ) : null}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function QrPreview({ qr }: { qr: FormQrCode }) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    void getFormQrBlob(qr)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (active) setSrc(null);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [qr.id, qr.file_url, qr.created_at]);

  return (
    <div className="flex h-40 w-40 shrink-0 items-center justify-center rounded border border-slate-200 bg-white p-3">
      {src ? <img alt={`QR ${qr.label}`} className="h-full w-full object-contain" src={src} /> : <div className="h-full w-full bg-white" />}
    </div>
  );
}
