"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { BarChart3, CalendarDays, Camera, ClipboardList, FileText, FileInput, Leaf, Map, PackageCheck, Recycle, Settings2, ShieldAlert, ShieldCheck, Users } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { AlertsTab } from "@/components/alerts/AlertsTab";
import { EventAuditTab } from "@/components/audit/EventAuditTab";
import { CarbonTab } from "@/components/carbon/CarbonTab";
import { EventDashboardTab } from "@/components/dashboard/EventDashboardTab";
import { EvidencesTab } from "@/components/evidences/EvidencesTab";
import { EventServicesTab } from "@/components/event-services/EventServicesTab";
import { EventFormsTab } from "@/components/event-forms/EventFormsTab";
import { EventSessionsTab } from "@/components/event-sessions/EventSessionsTab";
import { LogisticsOrdersTab } from "@/components/logistics/LogisticsOrdersTab";
import { IncidentsTab } from "@/components/incidents/IncidentsTab";
import { ReportsTab } from "@/components/reports/ReportsTab";
import { StaffTab } from "@/components/staff/StaffTab";
import { SurveysTab } from "@/components/surveys/SurveysTab";
import { TasksTab } from "@/components/tasks/TasksTab";
import { Card, CardContent } from "@/components/ui/card";
import { WasteTab } from "@/components/waste/WasteTab";
import { ZonesTab } from "@/components/zones/ZonesTab";
import type { Event } from "@/types/event";
import type { UserRole } from "@/types/roles";

const adminTabs = [
  { key: "resumen", label: "Resumen", icon: BarChart3, description: "Indicadores generales del evento y actividad reciente." },
  { key: "servicios", label: "Servicios", icon: Settings2, description: "Servicios contratados y valorizacion operacional." },
  { key: "logistica", label: "Logistica", icon: PackageCheck, description: "Pedidos logisticos asignados a operadores." },
  { key: "programacion", label: "Programacion", icon: CalendarDays, description: "Shows, jornadas y funciones del evento." },
  { key: "formularios", label: "Formularios", icon: FileInput, description: "Formularios publicos propios, QR y respuestas." },
  { key: "zonas", label: "Zonas", icon: Map, description: "Sectores, puntos criticos y cobertura del recinto." },
  { key: "personal", label: "Personal", icon: Users, description: "Equipo asignado, turnos y responsabilidades." },
  { key: "tareas", label: "Tareas", icon: ClipboardList, description: "Trabajo operativo planificado y avances en terreno." },
  { key: "incidencias", label: "Incidencias", icon: ShieldAlert, description: "Reportes, seguimiento y cierres de hallazgos." },
  { key: "evidencias", label: "Evidencias", icon: Camera, description: "Fotografias, documentos y respaldos del servicio." },
  { key: "residuos", label: "Residuos", icon: Recycle, description: "Registro, destino y recuperacion de residuos." },
  { key: "huella", label: "Huella", icon: Leaf, description: "Emisiones, consumos y factores ambientales." },
  { key: "encuestas", label: "Encuestas", icon: ClipboardList, description: "Respuestas importadas desde Google Forms o Sheets." },
  { key: "auditoria", label: "Auditoria", icon: ShieldCheck, description: "Trazabilidad interna del evento y acciones relevantes." },
  { key: "alertas", label: "Alertas", icon: ShieldAlert, description: "Avisos y riesgos operativos." },
  { key: "reportes", label: "Reportes", icon: FileText, description: "Informe final y entregables profesionales para cliente." }
];

const supervisorTabs = [
  { key: "resumen", label: "Resumen", icon: BarChart3, description: "Vista operativa del evento asignado." },
  { key: "logistica", label: "Logistica", icon: PackageCheck, description: "Pedidos logisticos para operadores asignados." },
  { key: "programacion", label: "Programacion", icon: CalendarDays, description: "Shows, jornadas y funciones asignadas." },
  { key: "formularios", label: "Formularios", icon: FileInput, description: "Links publicos, formularios activos y registros." },
  { key: "zonas", label: "Zonas", icon: Map, description: "Sectores y puntos de trabajo del recinto." },
  { key: "personal", label: "Personal", icon: Users, description: "Equipo disponible para la operacion." },
  { key: "tareas", label: "Tareas", icon: ClipboardList, description: "Trabajo operativo y seguimiento." },
  { key: "incidencias", label: "Incidencias", icon: ShieldAlert, description: "Reportes y hallazgos operativos." },
  { key: "evidencias", label: "Evidencias", icon: Camera, description: "Respaldo visual y documental." },
  { key: "residuos", label: "Residuos", icon: Recycle, description: "Registro ambiental del evento." },
  { key: "huella", label: "Huella", icon: Leaf, description: "Emisiones y consumos operativos." },
  { key: "encuestas", label: "Encuestas", icon: ClipboardList, description: "Google Forms, CSV y satisfaccion." },
  { key: "alertas", label: "Alertas", icon: ShieldAlert, description: "Avisos y riesgos operativos." },
  { key: "reportes", label: "Reportes", icon: FileText, description: "Informes y entregables del evento." }
];

function operationalState(event?: Event, variant?: "admin" | "supervisor") {
  if (!event || variant !== "supervisor") return { readOnly: false, message: "" };
  if (event.status === "REPORT_DELIVERED") return { readOnly: true, message: "Evento solo lectura: el reporte ya fue entregado." };
  if (event.status === "CANCELLED") return { readOnly: true, message: "Evento cancelado: no se permiten nuevos registros operativos." };
  if (event.status === "FINISHED") {
    const closureEndsAt = new Date(event.end_date);
    closureEndsAt.setDate(closureEndsAt.getDate() + 7);
    if (Date.now() > closureEndsAt.getTime()) return { readOnly: true, message: "Evento solo lectura: la ventana de cierre operativo ya termino." };
    return { readOnly: false, message: `Evento en cierre operativo hasta ${closureEndsAt.toLocaleDateString("es-CL")}.` };
  }
  return { readOnly: false, message: "" };
}

export function EventTabs({ eventId, event, role, variant = "admin" }: { eventId: string; event?: Event; role?: UserRole | null; variant?: "admin" | "supervisor" }) {
  const tabs = variant === "supervisor" ? supervisorTabs : adminTabs;
  const [active, setActive] = useState(tabs[0].key);
  const selected = tabs.find((tab) => tab.key === active) || tabs[0];
  const Icon = selected.icon;
  const state = operationalState(event, variant);
  const effectiveRole = state.readOnly && role === "SUPERVISOR" ? "CLIENT" : role;

  return (
    <div className="space-y-4">
      {state.message ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
          {state.message}
        </div>
      ) : null}
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
        <div className="flex min-w-max gap-2">
          {tabs.map((tab) => {
            const TabIcon = tab.icon;
            const isActive = tab.key === active;
            return (
              <button
                className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition ${
                  isActive ? "bg-emerald-700 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`}
                key={tab.key}
                onClick={() => setActive(tab.key)}
                type="button"
              >
                <TabIcon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>
      <TabContent active={active} description={selected.description} event={event} eventId={eventId} icon={<Icon className="h-10 w-10" />} role={effectiveRole} title={selected.label} />
    </div>
  );
}

function TabContent({ active, eventId, event, role, title, description, icon }: { active: string; eventId: string; event?: Event; role?: UserRole | null; title: string; description: string; icon: ReactNode }) {
  if (active === "resumen") return <EventDashboardTab eventId={eventId} />;
  if (active === "servicios") return <EventServicesTab eventId={eventId} role={role} />;
  if (active === "logistica") return <LogisticsOrdersTab eventId={eventId} eventName={event?.name} role={role} />;
  if (active === "programacion") return <EventSessionsTab eventId={eventId} role={role} />;
  if (active === "formularios") return <EventFormsTab eventId={eventId} role={role} />;
  if (active === "zonas") return <ZonesTab eventId={eventId} role={role} />;
  if (active === "personal") return <StaffTab eventId={eventId} role={role} />;
  if (active === "tareas") return <TasksTab eventId={eventId} role={role} />;
  if (active === "incidencias") return <IncidentsTab eventId={eventId} role={role} />;
  if (active === "evidencias") return <EvidencesTab eventId={eventId} role={role} />;
  if (active === "residuos") return <WasteTab eventId={eventId} role={role} />;
  if (active === "huella") return <CarbonTab eventId={eventId} role={role} />;
  if (active === "encuestas") return <SurveysTab eventId={eventId} role={role} />;
  if (active === "auditoria") return <EventAuditTab eventId={eventId} />;
  if (active === "alertas") return <AlertsTab eventId={eventId} role={role} />;
  if (active === "reportes") return <ReportsTab eventId={eventId} role={role} />;

  return (
    <Card>
      <CardContent className="p-6">
        <EmptyState icon={icon} title={title} description={`${description} Esta seccion queda preparada para la siguiente etapa funcional.`} />
      </CardContent>
    </Card>
  );
}
