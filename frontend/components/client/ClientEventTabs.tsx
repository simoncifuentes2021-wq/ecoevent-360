"use client";

import { useEffect, useMemo, useState } from "react";
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
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { getClientEventPortal } from "@/lib/api/clientPortal";
import type { ClientPortal, ClientPortalSectionKey } from "@/types/clientPortal";

type ClientTab = {
  key: string;
  sectionKey: ClientPortalSectionKey;
  label: string;
  icon: typeof BarChart3;
};

const allTabs: ClientTab[] = [
  { key: "resumen", sectionKey: "summary", label: "Resumen", icon: BarChart3 },
  { key: "servicios", sectionKey: "services", label: "Servicios", icon: BriefcaseBusiness },
  { key: "pedidos", sectionKey: "services", label: "Pedidos", icon: PackageCheck },
  { key: "avance", sectionKey: "operation", label: "Avance operativo", icon: ClipboardList },
  { key: "incidencias", sectionKey: "incidents", label: "Incidencias", icon: ShieldAlert },
  { key: "evidencias", sectionKey: "evidences", label: "Evidencias", icon: Camera },
  { key: "residuos", sectionKey: "waste", label: "Residuos", icon: Recycle },
  { key: "huella", sectionKey: "carbon", label: "Huella", icon: Cloud },
  { key: "formularios", sectionKey: "forms", label: "Formularios", icon: MessageSquare },
  { key: "bike_zone", sectionKey: "bike_zone", label: "Bike Zone", icon: MessageSquare },
  { key: "encuestas", sectionKey: "forms", label: "Encuestas", icon: MessageSquare },
  { key: "reportes", sectionKey: "reports", label: "Reportes", icon: FileText }
];

export function ClientEventTabs({ eventId }: { eventId: string }) {
  const [active, setActive] = useState("resumen");
  const [portal, setPortal] = useState<ClientPortal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activeRequest = true;
    setLoading(true);
    setError(null);
    void getClientEventPortal(eventId)
      .then((data) => {
        if (!activeRequest) return;
        setPortal(data);
      })
      .catch((err) => {
        if (activeRequest) setError(err instanceof Error ? err.message : "No se pudo cargar el portal cliente.");
      })
      .finally(() => {
        if (activeRequest) setLoading(false);
      });
    return () => { activeRequest = false; };
  }, [eventId]);

  const tabs = useMemo(() => {
    const enabled = new Set((portal?.sections ?? []).map((section) => section.section_key));
    return allTabs.filter((tab) => enabled.has(tab.sectionKey));
  }, [portal]);

  useEffect(() => {
    if (tabs.length && !tabs.some((tab) => tab.key === active)) setActive(tabs[0].key);
  }, [active, tabs]);

  if (loading) return <LoadingState label="Cargando portal cliente..." />;
  if (error) return <ErrorState title="No se pudo cargar el portal" message={error} />;
  if (!tabs.length) return <ErrorState title="Portal sin secciones visibles" message="El administrador aun no habilito secciones para este evento." />;

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
      {active === "bike_zone" ? <ClientFormsTab eventId={eventId} /> : null}
      {active === "encuestas" ? <ClientSurveysTab eventId={eventId} /> : null}
      {active === "reportes" ? <ClientReportsTab eventId={eventId} /> : null}
    </div>
  );
}
