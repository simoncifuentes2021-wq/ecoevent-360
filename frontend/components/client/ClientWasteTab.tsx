"use client";

import { useEffect, useState } from "react";

import { WasteCharts } from "@/components/waste/WasteCharts";
import { WasteRecordTable } from "@/components/waste/WasteRecordTable";
import { WasteSummaryCards } from "@/components/waste/WasteSummaryCards";
import { getWasteRecords, getWasteSummary } from "@/lib/api/waste";
import { getWasteTypes } from "@/lib/api/wasteTypes";
import { normalizeWasteSummary } from "@/lib/normalizers/waste";
import type { WasteRecord, WasteSummary, WasteType } from "@/types/waste";

export function ClientWasteTab({ eventId }: { eventId: string }) {
  const [summary, setSummary] = useState<WasteSummary>(normalizeWasteSummary(null));
  const [records, setRecords] = useState<WasteRecord[]>([]);
  const [types, setTypes] = useState<WasteType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [rawSummary, recordData, typeData] = await Promise.all([getWasteSummary(eventId), getWasteRecords(eventId), getWasteTypes().catch(() => [])]);
        setSummary(normalizeWasteSummary(rawSummary));
        setRecords(recordData.items);
        setTypes(typeData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudo cargar residuos.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [eventId]);

  return <div className="space-y-4"><WasteSummaryCards summary={summary} /><WasteCharts byDestination={summary.by_destination} byType={summary.by_type} byZone={summary.by_zone} /><WasteRecordTable canDelete={false} canEdit={false} error={error} loading={loading} records={records} wasteTypes={types} onDelete={() => {}} onEdit={() => {}} onView={() => {}} /></div>;
}
