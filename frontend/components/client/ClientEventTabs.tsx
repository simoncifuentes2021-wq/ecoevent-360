"use client";

import { useState } from "react";
import { BarChart3, BriefcaseBusiness, Camera, ClipboardList, Cloud, FileText, MessageSquare, PackageCheck, Recycle, ShieldAlert } from "lucide-react";

import { ClientCarbonTab } from "@/components/client/ClientCarbonTab";
import { ClientEvidencesTab } from "@/components/client/ClientEvidencesTab";
import { ClientEventSummaryTab } from "@/components/client/ClientEventSummaryTab";
import { ClientIncidentsTab } from "@/components/client/ClientIncidentsTab";
import { ClientOperationalProgressTab } from "@/components/client/ClientOperationalProgressTab";
import { ClientOrdersTab } from "@/components/client/ClientOrdersTab";
import { ClientReportsTab } from "@/components/client/ClientReportsTab";
import { ClientServicesTab } from "@/components/client/ClientServicesTab";
import { ClientFormsTab } from "@/components/client/ClientFormsTab";
import { ClientSurveysTab } from "@/components/client/ClientSurveysTab";
import { ClientWasteTab } from "@/components/client/ClientWasteTab";

const tabs = [
  { key: "resumen", label: "Resumen", icon: BarChart3 },
  { key: "servicios", label: "Servicios", icon: BriefcaseBusiness },
  { key: "pedidos", label: "Pedidos", icon: PackageCheck },
  { key: "avance", label: "Avance operativo", icon: ClipboardList },
  { key: "incidencias", label: "Incidencias", icon: ShieldAlert },
  { key: "evidencias", label: "Evidencias", icon: Camera },
  { key: "residuos", label: "Residuos", icon: Recycle },
  { key: "huella", label: "Huella", icon: Cloud },
  { key: "formularios", label: "Formularios", icon: MessageSquare },
  { key: "encuestas", label: "Encuestas", icon: MessageSquare },
  { key: "reportes", label: "Reportes", icon: FileText }
];

export function ClientEventTabs({ eventId }: { eventId: string }) {
  const [active, setActive] = useState("resumen");
  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
        <div className="flex min-w-max gap-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = active === tab.key;
            return <button className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition ${isActive ? "bg-emerald-700 text-white" : "text-slate-600 hover:bg-slate-100"}`} key={tab.key} onClick={() => setActive(tab.key)} type="button"><Icon className="h-4 w-4" />{tab.label}</button>;
          })}
        </div>
      </div>
      {active === "resumen" ? <ClientEventSummaryTab eventId={eventId} /> : null}
      {active === "servicios" ? <ClientServicesTab eventId={eventId} /> : null}
      {active === "pedidos" ? <ClientOrdersTab eventId={eventId} /> : null}
      {active === "avance" ? <ClientOperationalProgressTab eventId={eventId} /> : null}
      {active === "incidencias" ? <ClientIncidentsTab eventId={eventId} /> : null}
      {active === "evidencias" ? <ClientEvidencesTab eventId={eventId} /> : null}
      {active === "residuos" ? <ClientWasteTab eventId={eventId} /> : null}
      {active === "huella" ? <ClientCarbonTab eventId={eventId} /> : null}
      {active === "formularios" ? <ClientFormsTab eventId={eventId} /> : null}
      {active === "encuestas" ? <ClientSurveysTab eventId={eventId} /> : null}
      {active === "reportes" ? <ClientReportsTab eventId={eventId} /> : null}
    </div>
  );
}
