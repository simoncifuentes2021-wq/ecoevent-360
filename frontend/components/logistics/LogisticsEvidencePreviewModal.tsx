"use client";

import { useState } from "react";
import { Download, ExternalLink, FileText, RotateCcw, ZoomIn, ZoomOut } from "lucide-react";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { fileUrl } from "@/lib/files";
import type { LogisticsEvidence } from "@/types/logistics-evidence";

export function LogisticsEvidencePreviewModal({
  evidence,
  onClose
}: {
  evidence: LogisticsEvidence;
  onClose: () => void;
}) {
  const [zoom, setZoom] = useState(1);
  const url = fileUrl(evidence.file_url);
  const isImage = evidence.file_type?.startsWith("image/") || evidence.mime_type?.startsWith("image/");
  const isPdf = evidence.file_type === "application/pdf" || evidence.mime_type === "application/pdf";
  const title = evidence.notes || evidence.file_name || "Evidencia";
  const canZoomOut = zoom > 0.75;
  const canZoomIn = zoom < 3;

  return (
    <ModalShell title="Vista de evidencia" description={title} size="lg" onClose={onClose}>
      <div className="space-y-4">
        {isImage ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 p-2">
              <span className="text-sm font-semibold text-slate-700">{Math.round(zoom * 100)}%</span>
              <div className="flex gap-2">
                <Button
                  className="h-9 w-9 p-0"
                  disabled={!canZoomOut}
                  type="button"
                  variant="secondary"
                  onClick={() => setZoom((current) => Math.max(0.75, Number((current - 0.25).toFixed(2))))}
                >
                  <ZoomOut className="h-4 w-4" />
                </Button>
                <Button className="h-9 w-9 p-0" type="button" variant="secondary" onClick={() => setZoom(1)}>
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button
                  className="h-9 w-9 p-0"
                  disabled={!canZoomIn}
                  type="button"
                  variant="secondary"
                  onClick={() => setZoom((current) => Math.min(3, Number((current + 0.25).toFixed(2))))}
                >
                  <ZoomIn className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="max-h-[68vh] overflow-auto rounded-lg bg-slate-100 p-2">
              <div className="grid min-h-[18rem] place-items-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  alt={title}
                  className="max-w-none rounded-md object-contain transition-transform"
                  src={url}
                  style={{ width: `${zoom * 100}%` }}
                />
              </div>
            </div>
          </>
        ) : isPdf ? (
          <iframe className="h-[68vh] w-full rounded-lg border bg-slate-100" src={url} title={title} />
        ) : (
          <div className="grid min-h-[16rem] place-items-center rounded-lg border bg-slate-50 p-6 text-center">
            <div>
              <FileText className="mx-auto h-14 w-14 text-slate-500" />
              <p className="mt-3 text-sm font-semibold text-slate-800">Documento disponible</p>
              <p className="mt-1 text-sm text-slate-500">Este tipo de archivo no tiene vista previa integrada.</p>
            </div>
          </div>
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <a href={url} rel="noreferrer" target="_blank">
            <Button type="button" variant="secondary">
              <ExternalLink className="h-4 w-4" />
              Abrir aparte
            </Button>
          </a>
          <a download href={url} rel="noreferrer" target="_blank">
            <Button type="button" variant="secondary">
              <Download className="h-4 w-4" />
              Descargar
            </Button>
          </a>
        </div>
      </div>
    </ModalShell>
  );
}
