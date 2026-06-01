"use client";

import { Download, ExternalLink, QrCode } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { QrCode as QrCodeType } from "@/types/qr";

export function QrCodeCard({ qr, onDownload }: { qr: QrCodeType; onDownload: (qr: QrCodeType) => void }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-700"><QrCode className="h-6 w-6" /></span>
        <div className="min-w-0 flex-1">
          <h4 className="font-semibold text-slate-950">{qr.label}</h4>
          <p className="text-xs text-slate-500">{qr.zone?.name || "QR general"}</p>
          {qr.target_url ? <a className="mt-2 flex items-center gap-1 truncate text-sm text-emerald-700 hover:underline" href={qr.target_url} rel="noreferrer" target="_blank"><ExternalLink className="h-3.5 w-3.5" />{qr.target_url}</a> : null}
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <Button onClick={() => onDownload(qr)} size="sm" type="button" variant="secondary"><Download className="h-4 w-4" />Descargar</Button>
      </div>
    </div>
  );
}
