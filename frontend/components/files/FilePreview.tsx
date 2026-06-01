"use client";

import { FileText, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { FileUpload } from "@/types/file";

export function FilePreview({ upload, onClear }: { upload: FileUpload; onClear: () => void }) {
  const sizeMb = (upload.size / 1024 / 1024).toFixed(2);
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex items-center gap-3">
        {upload.previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={upload.name} className="h-16 w-16 rounded-xl object-cover" src={upload.previewUrl} />
        ) : (
          <div className="grid h-16 w-16 place-items-center rounded-xl bg-slate-100 text-slate-600"><FileText className="h-7 w-7" /></div>
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-950">{upload.name}</p>
          <p className="text-xs text-slate-500">{upload.contentType} · {sizeMb} MB</p>
        </div>
        <Button size="sm" type="button" variant="ghost" onClick={onClear}><X className="h-4 w-4" /></Button>
      </div>
    </div>
  );
}
