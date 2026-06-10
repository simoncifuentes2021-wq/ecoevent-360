"use client";

import { FileText, Image, Trash2, Eye } from "lucide-react";

import { Button } from "@/components/ui/button";
import { fileUrl } from "@/lib/files";
import type { Evidence } from "@/types/evidence";

function date(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "-";
}

export function EvidenceCard({ evidence, canDelete, onPreview, onDelete }: { evidence: Evidence; canDelete: boolean; onPreview: (item: Evidence) => void; onDelete: (item: Evidence) => void }) {
  const isImage = evidence.file_type?.startsWith("image/");
  const url = fileUrl(evidence.file_url);
  return (
    <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
      <button className="block h-44 w-full bg-slate-100 text-left" type="button" onClick={() => onPreview(evidence)}>
        {isImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={evidence.description || evidence.filename || "Evidencia"} className="h-full w-full object-cover" src={url} />
        ) : (
          <div className="grid h-full place-items-center text-slate-500"><FileText className="h-14 w-14" /></div>
        )}
      </button>
      <div className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-semibold text-slate-950">{evidence.description || evidence.filename || "Evidencia operacional"}</p>
            <p className="text-xs text-slate-500">{date(evidence.created_at || evidence.taken_at)}</p>
          </div>
          {isImage ? <Image className="h-5 w-5 text-emerald-700" /> : <FileText className="h-5 w-5 text-slate-500" />}
        </div>
        <div className="flex gap-2">
          <Button className="flex-1" size="sm" variant="secondary" onClick={() => onPreview(evidence)}><Eye className="h-4 w-4" />Ver</Button>
          {canDelete ? <Button size="sm" variant="ghost" onClick={() => onDelete(evidence)}><Trash2 className="h-4 w-4" /></Button> : null}
        </div>
      </div>
    </div>
  );
}
