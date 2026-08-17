"use client";

import { useEffect, useState } from "react";
import { Download, Eye, FileText } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { Button } from "@/components/ui/button";
import { downloadReportPublication, getEventReports, getReportPublications } from "@/lib/api/reports";
import type { Report, ReportPublication } from "@/types/report";

type Delivered = { report: Report; publication: ReportPublication };

export function ClientReportsTab({ eventId }: { eventId: string }) {
  const [items, setItems] = useState<Delivered[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const reports = await getEventReports(eventId);
        const publications = await Promise.all(
          reports.items.map(async report => ({ report, publications: await getReportPublications(report.id) }))
        );
        setItems(publications.flatMap(({ report, publications: versions }) =>
          versions.filter(version => version.status === "DELIVERED").map(publication => ({ report, publication }))
        ));
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudieron cargar los reportes.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [eventId]);

  async function open(publicationId: string, inline: boolean) {
    const blob = await downloadReportPublication(publicationId, inline);
    const url = URL.createObjectURL(blob);
    if (inline) window.open(url, "_blank", "noopener,noreferrer");
    else {
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `reporte-${publicationId}.pdf`;
      anchor.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }

  if (loading) return <LoadingState label="Cargando reportes..." />;
  if (error) return <ErrorState message={error} />;
  if (!items.length) return <div className="rounded-2xl border border-dashed p-10 text-center text-slate-500"><FileText className="mx-auto mb-3 h-8 w-8"/>Aún no hay publicaciones entregadas.</div>;
  return <div className="grid gap-4 md:grid-cols-2">{items.map(({ report, publication }) => <article className="rounded-2xl border bg-white p-5 shadow-sm" key={publication.id}><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-widest text-emerald-600">{report.scope === "SHOW" ? "Reporte de show" : "Reporte de evento"}</p><h3 className="mt-2 text-lg font-bold">{report.title}</h3><p className="mt-1 text-sm text-slate-500">Versión {publication.publication_number} · {publication.page_count} páginas</p><p className="text-xs text-slate-400">Entregada {publication.delivered_at ? new Date(publication.delivered_at).toLocaleDateString("es-CL", { timeZone: "America/Santiago" }) : ""}</p></div><span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">Entregado</span></div><div className="mt-5 flex gap-2"><Button variant="secondary" onClick={() => void open(publication.id, true)}><Eye className="h-4 w-4"/>Ver reporte</Button><Button onClick={() => void open(publication.id, false)}><Download className="h-4 w-4"/>Descargar PDF</Button></div></article>)}</div>;
}
