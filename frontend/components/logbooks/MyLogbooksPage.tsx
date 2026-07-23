"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ClipboardCheck } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { getMyLogbooks } from "@/lib/api/logbooks";
import { logbookError } from "@/lib/logbook-errors";
import { logbookLabel, logbookStatusLabels } from "@/lib/logbook-labels";
import type { LogbookAssignment } from "@/types/logbook";

const filters = ["ALL", "PENDING", "IN_PROGRESS", "SUBMITTED", "RESUBMITTED", "CHANGES_REQUESTED", "APPROVED", "OVERDUE"];

export function MyLogbooksPage() {
  const [items, setItems] = useState<LogbookAssignment[]>([]);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    getMyLogbooks(filter === "ALL" ? undefined : filter)
      .then(setItems)
      .catch((reason) => setError(logbookError(reason, "No se pudieron cargar tus bitácoras.")))
      .finally(() => setLoading(false));
  };

  useEffect(load, [filter]);

  return (
    <div className="space-y-6">
      <PageHeader title="Mis bitácoras" description="Completa y consulta tus procedimientos asignados." />
      <select className="w-full rounded-xl border bg-white p-3 md:w-72" value={filter} onChange={(event) => setFilter(event.target.value)}>
        {filters.map((value) => (
          <option key={value} value={value}>{value === "ALL" ? "Todos los estados" : logbookLabel(logbookStatusLabels, value)}</option>
        ))}
      </select>
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={load} /> : items.length === 0 ? (
        <EmptyState icon={<ClipboardCheck />} title="No hay bitácoras para este filtro" description="Las nuevas asignaciones aparecerán aquí." />
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Link className="block rounded-xl border bg-white p-4 transition hover:border-emerald-500" href={`/worker/mis-bitacoras/${item.logbook_instance_id}`} key={item.id}>
              <div className="flex justify-between gap-3">
                <span className="font-medium">Bitácora asignada</span>
                <span className="text-sm text-emerald-700">{logbookLabel(logbookStatusLabels, item.status)}</span>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                {item.attempt_number > 1 ? "Reenvío" : "Envío inicial"} · Intento {item.attempt_number}
              </p>
              {item.review_comment ? <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{item.review_comment}</p> : null}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
