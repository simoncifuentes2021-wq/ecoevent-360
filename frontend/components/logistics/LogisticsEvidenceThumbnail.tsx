"use client";

import { ImageOff, Loader2 } from "lucide-react";

import { usePrivateFileUrl } from "@/hooks/usePrivateFileUrl";
import type { LogisticsEvidence } from "@/types/logistics-evidence";

export function LogisticsEvidenceThumbnail({
  evidence,
  className
}: {
  evidence: LogisticsEvidence;
  className: string;
}) {
  const { url, error } = usePrivateFileUrl(evidence.file_url);

  if (url) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        alt={evidence.notes || evidence.file_name || "Evidencia logistica"}
        className={className}
        src={url}
      />
    );
  }

  return (
    <div
      className={`${className} grid place-items-center bg-slate-100 text-slate-500`}
      title={error || "Cargando evidencia..."}
    >
      {error ? <ImageOff className="h-6 w-6" /> : <Loader2 className="h-6 w-6 animate-spin" />}
      <span className="sr-only">{error || "Cargando evidencia..."}</span>
    </div>
  );
}
