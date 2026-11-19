"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ReactNode } from "react";
import { CalendarDays, Recycle, Scale, Users, UserRoundCheck, PackageCheck } from "lucide-react";

import type { VolunteerDashboard } from "@/types/volunteer";

const number = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 3 });
const kg = (value: string | number) => `${number.format(Number(value) || 0)} kg`;

export function VolunteerDashboardPanel({ data }: { data: VolunteerDashboard | null }) {
  if (!data) return <div className="rounded-2xl border bg-white p-8 text-center text-sm text-slate-500">Selecciona un evento para ver sus indicadores.</div>;

  const metrics = [
    { label: "Voluntarios únicos", value: number.format(data.unique_volunteers), icon: Users, color: "bg-sky-50 text-sky-700" },
    { label: "Participaciones", value: number.format(data.participations), icon: UserRoundCheck, color: "bg-violet-50 text-violet-700" },
    { label: "Entregas registradas", value: number.format(data.contributions), icon: PackageCheck, color: "bg-amber-50 text-amber-700" },
    { label: "Material recuperado", value: kg(data.total_weight_kg), icon: Scale, color: "bg-emerald-50 text-emerald-700" },
    { label: "Activaciones activas", value: number.format(data.active_activations), icon: CalendarDays, color: "bg-indigo-50 text-indigo-700" },
    { label: "Promedio por voluntario", value: kg(data.average_per_volunteer_kg), icon: Recycle, color: "bg-teal-50 text-teal-700" },
  ];

  return <section className="space-y-5" aria-label="Resumen de reciclaje">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {metrics.map((item) => <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm" key={item.label}>
        <div className="flex items-start justify-between gap-3"><p className="text-sm font-medium text-slate-500">{item.label}</p><span className={`grid h-10 w-10 place-items-center rounded-xl ${item.color}`}><item.icon className="h-5 w-5" /></span></div>
        <p className="mt-4 text-2xl font-bold tracking-tight text-slate-950">{item.value}</p>
      </article>)}
    </div>
    <div className="grid gap-4 xl:grid-cols-2">
      <ChartCard title="Kilos por fecha" empty={!data.by_date.length}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={data.by_date} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip formatter={(value) => [kg(String(value)), "Material"]} /><Bar dataKey="kg" fill="#07846d" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Recuperación por activación" empty={!data.by_activation.length}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={data.by_activation} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} /><YAxis tick={{ fontSize: 11 }} /><Tooltip formatter={(value) => [kg(String(value)), "Material"]} /><Bar dataKey="kg" fill="#0e7490" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Kilos por material" empty={!data.by_material.length}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={data.by_material} layout="vertical" margin={{ top: 8, right: 14, left: 8, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" tick={{ fontSize: 11 }} /><YAxis type="category" dataKey="material" width={110} tick={{ fontSize: 11 }} /><Tooltip formatter={(value) => [kg(String(value)), "Material"]} /><Bar dataKey="kg" fill="#7c3aed" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Nuevos voluntarios por fecha" empty={!data.new_volunteers_by_date.length}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={data.new_volunteers_by_date} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="volunteers" fill="#d97706" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer>
      </ChartCard>
    </div>
  </section>;
}

function ChartCard({ title, empty, children }: { title: string; empty: boolean; children: ReactNode }) {
  return <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
    <h2 className="mb-3 font-semibold text-slate-900">{title}</h2>
    <div className="h-64">{empty ? <div className="grid h-full place-items-center rounded-xl bg-slate-50 text-sm text-slate-500">Aún no hay datos para mostrar.</div> : children}</div>
  </article>;
}
