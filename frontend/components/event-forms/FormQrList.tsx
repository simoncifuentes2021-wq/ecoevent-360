"use client";

import { Download, Trash2 } from "lucide-react";

import { CopyPublicLinkButton } from "@/components/event-forms/CopyPublicLinkButton";
import { Button } from "@/components/ui/button";
import { downloadFormQrCode } from "@/lib/api/formQr";
import type { FormQrCode } from "@/types/formQr";

export function FormQrList({ items, canDelete, onDelete }: { items: FormQrCode[]; canDelete: boolean; onDelete: (qr: FormQrCode) => void }) {
  if (!items.length) return <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">Todavía no hay QR generados para este formulario.</p>;
  return (
    <div className="grid gap-3">
      {items.map((qr) => (
        <article className="rounded-lg border bg-white p-3" key={qr.id}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="font-bold text-slate-950">{qr.label}</p>
              <p className="text-xs font-semibold text-slate-500">{qr.qr_type}{qr.language ? ` · ${qr.language}` : ""}</p>
              <p className="mt-1 break-all text-xs text-emerald-700">{qr.target_url}</p>
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
