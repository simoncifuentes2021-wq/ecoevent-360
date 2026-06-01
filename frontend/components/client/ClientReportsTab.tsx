"use client";

import { useEffect, useState } from "react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ReportDetailDrawer } from "@/components/reports/ReportDetailDrawer";
import { ReportList } from "@/components/reports/ReportList";
import { getEventReports } from "@/lib/api/reports";
import { normalizeReport } from "@/lib/normalizers/reports";
import type { Report } from "@/types/report";

export function ClientReportsTab({ eventId }: { eventId: string }) {
  const [reports, setReports] = useState<Report[]>([]);
  const [detail, setDetail] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getEventReports(eventId);
        setReports(data.items.map(normalizeReport));
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudieron cargar los reportes.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [eventId]);

  if (loading) return <LoadingState label="Cargando reportes..." />;
  if (error) return <ErrorState message={error} />;
  return <><ReportList canDelete={false} canDeliver={false} reports={reports} onDelete={() => {}} onDeliver={() => {}} onView={setDetail} /><ReportDetailDrawer report={detail} onClose={() => setDetail(null)} /></>;
}
