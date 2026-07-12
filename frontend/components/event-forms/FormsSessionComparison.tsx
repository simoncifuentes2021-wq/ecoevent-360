"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { getFormsSessionComparison } from "@/lib/api/eventForms";
import type { EventFormType, FormsSessionComparisonItem } from "@/types/eventForm";

type FormTypeFilter = "" | EventFormType;

const filterLabels: Array<{ value: FormTypeFilter; label: string }> = [
  { value: "", label: "Todos los formularios" },
  { value: "EXPERIENCE_SURVEY", label: "Experiencia" },
  { value: "TRANSPORT_SURVEY", label: "Transporte" },
  { value: "BIKE_ZONE_REGISTRATION", label: "Bike Zone" }
];

export function FormsSessionComparison({ eventId, compact = false }: { eventId: string; compact?: boolean }) {
  const [filter, setFilter] = useState<FormTypeFilter>("");
  const [sessions, setSessions] = useState<FormsSessionComparisonItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void getFormsSessionComparison(eventId, filter)
      .then((data) => {
        if (active) setSessions(data.sessions);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "No se pudo cargar la comparacion por show.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [eventId, filter]);

  const responseData = useMemo(() => sessions.map((session) => ({
    name: session.session_name,
    respuestas: session.total_responses,
    bikeZone: session.bike_zone_total
  })), [sessions]);

  const ratingData = useMemo(() => sessions
    .filter((session) => session.average_rating !== null && session.average_rating !== undefined)
    .map((session) => ({ name: session.session_name, nota: session.average_rating ?? 0 })), [sessions]);

  const hasTransport = sessions.some((session) => session.transport_modes.length > 0);
  const hasProblems = sessions.some((session) => session.main_problems.length > 0);

  return (
    <section className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-950">Comparativo por show</h3>
          <p className="text-sm text-slate-600">Resultados agregados de formularios por sesion, sin datos personales.</p>
        </div>
        <select
          className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700"
          value={filter}
          onChange={(event) => setFilter(event.target.value as FormTypeFilter)}
        >
          {filterLabels.map((item) => <option key={item.value || "all"} value={item.value}>{item.label}</option>)}
        </select>
      </div>

      {loading ? <LoadingState label="Cargando comparativo..." /> : null}
      {error ? <ErrorState message={error} /> : null}

      {!loading && !error && !sessions.length ? (
        <div className="mt-4 rounded-lg bg-slate-50 p-5 text-sm text-slate-500">No hay shows para comparar todavia.</div>
      ) : null}

      {!loading && !error && sessions.length ? (
        <div className="mt-4 space-y-4">
          {!compact ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {sessions.map((session) => (
                <article className="rounded-lg border border-slate-200 bg-slate-50 p-4" key={session.session_id}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h4 className="font-bold text-slate-950">{session.session_name}</h4>
                      <p className="text-xs text-slate-500">{formatSessionDate(session)}</p>
                    </div>
                    <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600">{session.active_forms}/{session.total_forms} activos</span>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                    <Metric label="Respuestas" value={session.total_responses} />
                    <Metric label="Nota prom." value={session.average_rating !== null && session.average_rating !== undefined ? session.average_rating.toFixed(1) : "-"} />
                    <Metric label="Recomienda" value={session.recommendation_rate !== null && session.recommendation_rate !== undefined ? `${Math.round(session.recommendation_rate)}%` : "-"} />
                    <Metric label="Bike Zone" value={session.bike_zone_total} />
                  </div>
                </article>
              ))}
            </div>
          ) : null}

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartBox title="Respuestas por show" empty={!responseData.some((item) => item.respuestas > 0 || item.bikeZone > 0)}>
              <ResponsiveContainer height="100%" width="100%">
                <BarChart data={responseData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="respuestas" fill="#0f766e" name="Respuestas" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="bikeZone" fill="#0369a1" name="Bike Zone" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartBox>

            <ChartBox title="Nota promedio por show" empty={!ratingData.length}>
              <ResponsiveContainer height="100%" width="100%">
                <LineChart data={ratingData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 7]} />
                  <Tooltip />
                  <Line dataKey="nota" name="Nota promedio" stroke="#0f766e" strokeWidth={3} type="monotone" />
                </LineChart>
              </ResponsiveContainer>
            </ChartBox>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Show</th>
                  <th className="px-3 py-2">Fecha</th>
                  <th className="px-3 py-2">Forms</th>
                  <th className="px-3 py-2">Respuestas</th>
                  <th className="px-3 py-2">Nota</th>
                  <th className="px-3 py-2">Recomienda</th>
                  <th className="px-3 py-2">Bike Zone</th>
                  <th className="px-3 py-2">Check-in</th>
                  <th className="px-3 py-2">Check-out</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr className="border-t align-top" key={session.session_id}>
                    <td className="px-3 py-2 font-semibold text-slate-900">{session.session_name}</td>
                    <td className="px-3 py-2 text-slate-600">{formatSessionDate(session)}</td>
                    <td className="px-3 py-2">{session.active_forms}/{session.total_forms}</td>
                    <td className="px-3 py-2">{session.total_responses}</td>
                    <td className="px-3 py-2">{formatNullableNumber(session.average_rating, 1)}</td>
                    <td className="px-3 py-2">{formatPercent(session.recommendation_rate)}</td>
                    <td className="px-3 py-2">{session.bike_zone_total}</td>
                    <td className="px-3 py-2">{session.bike_zone_checked_in}</td>
                    <td className="px-3 py-2">{session.bike_zone_checked_out}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Breakdown title="Transporte por show" empty={!hasTransport} sessions={sessions} field="transport_modes" />
            <Breakdown title="Problemas principales por show" empty={!hasProblems} sessions={sessions} field="main_problems" />
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md bg-white p-3">
      <p className="text-[11px] font-bold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-black text-slate-950">{value}</p>
    </div>
  );
}

function ChartBox({ title, empty, children }: { title: string; empty: boolean; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <h4 className="font-bold text-slate-950">{title}</h4>
      <div className="mt-3 h-64">
        {empty ? <div className="grid h-full place-items-center rounded-md bg-slate-50 text-sm text-slate-500">Sin datos suficientes.</div> : children}
      </div>
    </div>
  );
}

function Breakdown({ title, empty, sessions, field }: { title: string; empty: boolean; sessions: FormsSessionComparisonItem[]; field: "transport_modes" | "main_problems" }) {
  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <h4 className="font-bold text-slate-950">{title}</h4>
      {empty ? <p className="mt-3 rounded-md bg-slate-50 p-4 text-sm text-slate-500">Sin datos suficientes.</p> : null}
      {!empty ? (
        <div className="mt-3 space-y-3">
          {sessions.map((session) => (
            <div className="rounded-md bg-slate-50 p-3" key={session.session_id}>
              <p className="text-sm font-bold text-slate-900">{session.session_name}</p>
              {session[field].length ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  {session[field].map((item) => <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700" key={item.name}>{item.name}: {item.value}</span>)}
                </div>
              ) : <p className="mt-2 text-xs text-slate-500">Sin registros.</p>}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function formatSessionDate(session: FormsSessionComparisonItem) {
  const parts = [session.session_date, session.start_time].filter(Boolean);
  return parts.length ? parts.join(" ") : "Sin fecha";
}

function formatNullableNumber(value?: number | null, digits = 0) {
  return value === null || value === undefined ? "-" : value.toFixed(digits);
}

function formatPercent(value?: number | null) {
  return value === null || value === undefined ? "-" : `${Math.round(value)}%`;
}
