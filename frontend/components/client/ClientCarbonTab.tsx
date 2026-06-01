"use client";

import { useEffect, useState } from "react";

import { CarbonCharts } from "@/components/carbon/CarbonCharts";
import { CarbonRecordTable } from "@/components/carbon/CarbonRecordTable";
import { CarbonSummaryCards } from "@/components/carbon/CarbonSummaryCards";
import { getCarbonRecords, getCarbonSummary } from "@/lib/api/carbon";
import { normalizeCarbonSummary } from "@/lib/normalizers/carbon";
import type { CarbonRecord, CarbonSummary } from "@/types/carbon";

export function ClientCarbonTab({ eventId }: { eventId: string }) {
  const [summary, setSummary] = useState<CarbonSummary>(normalizeCarbonSummary(null));
  const [records, setRecords] = useState<CarbonRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [rawSummary, recordData] = await Promise.all([getCarbonSummary(eventId), getCarbonRecords(eventId)]);
        setSummary(normalizeCarbonSummary(rawSummary));
        setRecords(recordData.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudo cargar la huella.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [eventId]);

  return <div className="space-y-4"><CarbonSummaryCards summary={summary} /><CarbonCharts byCategory={summary.by_category} byDate={summary.by_date} byScope={summary.by_scope} bySource={summary.by_source} /><CarbonRecordTable canDelete={false} canEdit={false} error={error} loading={loading} records={records} onDelete={() => {}} onEdit={() => {}} onView={() => {}} /></div>;
}
