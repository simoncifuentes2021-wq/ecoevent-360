import { AlertTriangle, CheckCircle2, ClipboardCheck, ShieldAlert } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatDashboardPercentage } from "@/lib/normalizers/dashboard";
import type { EventDashboard } from "@/types/dashboard";

function MetricLine({ label, value, tone = "slate" }: { label: string; value: number; tone?: "slate" | "emerald" | "amber" | "rose" }) {
  const tones = { slate: "text-slate-900", emerald: "text-emerald-700", amber: "text-amber-700", rose: "text-rose-700" };
  return <div className="flex items-center justify-between gap-3 border-b border-slate-100 py-2.5 last:border-0"><span className="text-sm text-slate-600">{label}</span><span className={`text-sm font-bold ${tones[tone]}`}>{value}</span></div>;
}

export function EventControlSummary({ dashboard }: { dashboard: EventDashboard }) {
  const hasTasks = dashboard.tasks.total > 0;
  const hasIncidents = dashboard.incidents.total > 0 || dashboard.incidents.open > 0 || dashboard.incidents.resolved > 0;
  if (!hasTasks && !hasIncidents) return null;

  return (
    <div className={hasTasks && hasIncidents ? "grid gap-5 xl:grid-cols-[1.15fr_0.85fr]" : "space-y-5"}>
      {hasTasks ? (
        <Card className="border-slate-200/80 shadow-[0_12px_32px_-24px_rgba(15,23,42,0.45)]">
          <CardHeader className="flex items-center justify-between gap-4 bg-slate-50/70">
            <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Control operativo</p><h3 className="mt-1 text-base font-bold text-slate-950">Avance de tareas</h3></div>
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-100 text-emerald-700"><ClipboardCheck className="h-5 w-5" /></span>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between gap-4"><div><p className="text-4xl font-bold tracking-tight text-slate-950">{formatDashboardPercentage(dashboard.tasks.completion_rate)}</p><p className="mt-1 text-sm text-slate-500">Cumplimiento del plan operativo</p></div><p className="text-right text-sm font-semibold text-slate-700">{dashboard.tasks.completed} / {dashboard.tasks.total}<span className="block text-xs font-normal text-slate-500">completadas</span></p></div>
            <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-teal-400" style={{ width: `${Math.min(100, Math.max(0, dashboard.tasks.completion_rate))}%` }} /></div>
            <div className="mt-4 grid gap-x-6 sm:grid-cols-3">{dashboard.tasks.by_status.slice(0, 3).map((item) => <MetricLine key={item.name} label={item.name} value={item.value} />)}</div>
          </CardContent>
        </Card>
      ) : null}
      {hasIncidents ? (
        <Card className="border-slate-200/80 shadow-[0_12px_32px_-24px_rgba(15,23,42,0.45)]">
          <CardHeader className="flex items-center justify-between gap-4 bg-slate-50/70">
            <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-700">Gestión de riesgos</p><h3 className="mt-1 text-base font-bold text-slate-950">Incidencias y alertas</h3></div>
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-amber-100 text-amber-700"><ShieldAlert className="h-5 w-5" /></span>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <div className="flex items-center gap-3 rounded-xl bg-rose-50 px-4 py-3"><AlertTriangle className="h-5 w-5 text-rose-600" /><div><p className="text-2xl font-bold text-rose-700">{dashboard.incidents.open}</p><p className="text-xs font-semibold text-rose-700/80">Abiertas</p></div></div>
            <div className="flex items-center gap-3 rounded-xl bg-emerald-50 px-4 py-3"><CheckCircle2 className="h-5 w-5 text-emerald-600" /><div><p className="text-2xl font-bold text-emerald-700">{dashboard.incidents.resolved}</p><p className="text-xs font-semibold text-emerald-700/80">Resueltas</p></div></div>
            {dashboard.alerts && dashboard.alerts.critical > 0 ? <div className="flex items-center gap-3 rounded-xl bg-amber-50 px-4 py-3"><ShieldAlert className="h-5 w-5 text-amber-600" /><div><p className="text-2xl font-bold text-amber-700">{dashboard.alerts.critical}</p><p className="text-xs font-semibold text-amber-700/80">Críticas</p></div></div> : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
