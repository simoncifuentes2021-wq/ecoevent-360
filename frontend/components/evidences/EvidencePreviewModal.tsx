"use client";

import { Download, FileText } from "lucide-react";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { fileUrl } from "@/lib/files";
import type { Evidence } from "@/types/evidence";

export function EvidencePreviewModal({ evidence, onClose }: { evidence: Evidence; onClose: () => void }) {
  const isImage = evidence.file_type?.startsWith("image/");
  const url = fileUrl(evidence.file_url);
  return (
    <ModalShell title="Vista de evidencia" description={evidence.description || evidence.filename || "Archivo operativo"} onClose={onClose}>
      <div className="space-y-4">
        {isImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={evidence.description || "Evidencia"} className="max-h-[65vh] w-full rounded-2xl object-contain bg-slate-100" src={url} />
        ) : (
          <div className="rounded-2xl border bg-slate-50 p-6 text-center">
            <FileText className="mx-auto h-16 w-16 text-slate-500" />
            <p className="mt-3 text-sm text-slate-600">PDF o documento disponible para abrir en una pestaña nueva.</p>
          </div>
        )}
        <a href={url} rel="noreferrer" target="_blank">
          <Button className="w-full"><Download className="h-4 w-4" />Abrir archivo</Button>
        </a>
      </div>
    </ModalShell>
  );
}
