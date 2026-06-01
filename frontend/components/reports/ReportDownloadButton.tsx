"use client";

import { useState } from "react";
import { Download, ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import { downloadReport } from "@/lib/api/reports";
import { getReportFilename } from "@/lib/normalizers/reports";
import type { Report } from "@/types/report";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function ReportDownloadButton({ report }: { report: Report }) {
  const [loading, setLoading] = useState(false);

  async function handleDownload() {
    setLoading(true);
    try {
      if (report.pdf_url || report.file_url) {
        window.open(report.pdf_url || report.file_url || "", "_blank");
        return;
      }
      const response = await downloadReport(report.id);
      if (response.blob) downloadBlob(response.blob, response.filename || getReportFilename(report));
      else if (response.pdf_url || response.file_url) window.open(response.pdf_url || response.file_url, "_blank");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button disabled={loading} onClick={handleDownload} size="sm" type="button" variant="secondary">
      {report.pdf_url || report.file_url ? <ExternalLink className="h-4 w-4" /> : <Download className="h-4 w-4" />}
      {loading ? "Descargando..." : "Descargar"}
    </Button>
  );
}
