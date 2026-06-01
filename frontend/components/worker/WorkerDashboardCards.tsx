"use client";

import Link from "next/link";
import { AlertTriangle, Camera, ClipboardList, Flame, ListChecks, PlayCircle, Recycle } from "lucide-react";

import { cn } from "@/lib/utils";

export function WorkerDashboardCards({
  pending,
  inProgress,
  completedToday,
  critical
}: {
  pending: number;
  inProgress: number;
  completedToday: number;
  critical: number;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <StatCard href="/worker/mis-tareas" label="Pendientes" value={pending} icon={<ListChecks className="h-5 w-5" />} tone="warning" />
      <StatCard href="/worker/mis-tareas" label="En progreso" value={inProgress} icon={<PlayCircle className="h-5 w-5" />} tone="info" />
      <StatCard href="/worker/mis-tareas" label="Completadas hoy" value={completedToday} icon={<ClipboardList className="h-5 w-5" />} tone="success" />
      <StatCard href="/worker/mis-tareas" label="Criticas" value={critical} icon={<Flame className="h-5 w-5" />} tone="danger" />
    </div>
  );
}

export function WorkerQuickActions() {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <ActionButton href="/worker/mis-tareas" label="Ver mis tareas" icon={<ClipboardList className="h-5 w-5" />} />
      <ActionButton href="/worker/reportar-incidencia" label="Reportar incidencia" icon={<AlertTriangle className="h-5 w-5" />} />
      <ActionButton href="/worker/subir-evidencia" label="Subir evidencia" icon={<Camera className="h-5 w-5" />} />
      <ActionButton href="/worker/registrar-residuo" label="Registrar residuo" icon={<Recycle className="h-5 w-5" />} />
    </div>
  );
}

function StatCard({
  href,
  label,
  value,
  icon,
  tone
}: {
  href: string;
  label: string;
  value: number;
  icon: React.ReactNode;
  tone: "success" | "warning" | "info" | "danger";
}) {
  return (
    <Link
      className={cn(
        "rounded-3xl border bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md",
        tone === "success" && "border-emerald-200",
        tone === "warning" && "border-amber-200",
        tone === "info" && "border-sky-200",
        tone === "danger" && "border-rose-200"
      )}
      href={href}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-600">{label}</p>
          <p className="mt-2 text-3xl font-bold text-slate-950">{value}</p>
        </div>
        <span
          className={cn(
            "grid h-10 w-10 place-items-center rounded-2xl",
            tone === "success" && "bg-emerald-50 text-emerald-700",
            tone === "warning" && "bg-amber-50 text-amber-700",
            tone === "info" && "bg-sky-50 text-sky-700",
            tone === "danger" && "bg-rose-50 text-rose-700"
          )}
        >
          {icon}
        </span>
      </div>
    </Link>
  );
}

function ActionButton({ href, label, icon }: { href: string; label: string; icon: React.ReactNode }) {
  return (
    <Link className="flex items-center gap-3 rounded-3xl border bg-white p-4 shadow-sm hover:bg-emerald-50" href={href}>
      <span className="grid h-11 w-11 place-items-center rounded-2xl bg-emerald-50 text-emerald-700">{icon}</span>
      <span className="text-sm font-semibold text-slate-900">{label}</span>
    </Link>
  );
}

