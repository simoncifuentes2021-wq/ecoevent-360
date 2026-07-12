"use client";

import { useEffect, useMemo, useState } from "react";
import { Eye, LayoutTemplate, Save } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { Button } from "@/components/ui/button";
import { applyClientPortalTemplate, getClientPortalConfig, getClientPortalPreview, updateClientPortalConfig } from "@/lib/api/clientPortal";
import type { ClientPortal, ClientPortalConfig, ClientPortalSection, ClientPortalWidget } from "@/types/clientPortal";

const templates = [
  { key: "completa_sin_datos_personales", label: "Completa sin datos personales" },
  { key: "ambiental", label: "Ambiental" },
  { key: "operativa", label: "Operativa" },
  { key: "experiencia", label: "Experiencia" },
  { key: "bike_zone", label: "Bike Zone" }
];

export function ClientPortalConfigTab({ eventId }: { eventId: string }) {
  const [config, setConfig] = useState<ClientPortalConfig | null>(null);
  const [preview, setPreview] = useState<ClientPortal | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setConfig(await getClientPortalConfig(eventId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la configuracion del portal cliente.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [eventId]);

  const widgetsBySection = useMemo(() => {
    const grouped: Record<string, ClientPortalWidget[]> = {};
    for (const widget of config?.widgets ?? []) {
      grouped[widget.section_key] = [...(grouped[widget.section_key] ?? []), widget];
    }
    return grouped;
  }, [config]);

  function toggleSection(section: ClientPortalSection) {
    if (!config) return;
    const enabled = !section.is_enabled;
    setConfig({
      ...config,
      sections: config.sections.map((item) => item.section_key === section.section_key ? { ...item, is_enabled: enabled } : item),
      widgets: config.widgets.map((widget) => widget.section_key === section.section_key ? { ...widget, is_enabled: enabled } : widget)
    });
  }

  function toggleWidget(widget: ClientPortalWidget) {
    if (!config) return;
    setConfig({
      ...config,
      widgets: config.widgets.map((item) => item.widget_key === widget.widget_key ? { ...item, is_enabled: !item.is_enabled } : item)
    });
  }

  async function save() {
    if (!config) return;
    setSaving(true);
    setError(null);
    try {
      setConfig(await updateClientPortalConfig(eventId, {
        scope: config.scope,
        is_active: config.is_active,
        sections: config.sections.map(({ section_key, label, is_enabled, sort_order }) => ({ section_key, label, is_enabled, sort_order })),
        widgets: config.widgets.map(({ widget_key, section_key, label, is_enabled, sort_order, visibility_config }) => ({ widget_key, section_key, label, is_enabled, sort_order, visibility_config }))
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar la configuracion.");
    } finally {
      setSaving(false);
    }
  }

  async function applyTemplate(templateKey: string) {
    setSaving(true);
    setError(null);
    try {
      setConfig(await applyClientPortalTemplate(eventId, templateKey));
      setPreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo aplicar la plantilla.");
    } finally {
      setSaving(false);
    }
  }

  async function loadPreview() {
    setSaving(true);
    setError(null);
    try {
      setPreview(await getClientPortalPreview(eventId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la vista previa.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState label="Cargando portal cliente..." />;
  if (error && !config) return <ErrorState message={error} title="No se pudo cargar" onRetry={load} />;
  if (!config) return null;

  return (
    <div className="space-y-4">
      {error ? <ErrorState message={error} /> : null}
      <div className="rounded-lg border bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-slate-950">Portal cliente</h3>
            <p className="text-sm text-slate-600">Define que secciones e indicadores puede ver el cliente en este evento.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={saving} type="button" variant="secondary" onClick={loadPreview}><Eye className="h-4 w-4" />Vista previa</Button>
            <Button disabled={saving} type="button" onClick={save}><Save className="h-4 w-4" />{saving ? "Guardando..." : "Guardar"}</Button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {templates.map((template) => (
            <Button disabled={saving} key={template.key} size="sm" type="button" variant="secondary" onClick={() => applyTemplate(template.key)}>
              <LayoutTemplate className="h-4 w-4" />
              {template.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border bg-white p-4">
          <h4 className="font-bold text-slate-950">Secciones visibles</h4>
          <div className="mt-3 grid gap-2">
            {config.sections.map((section) => (
              <label className="flex items-center justify-between gap-3 rounded border p-3 text-sm" key={section.section_key}>
                <span className="font-semibold text-slate-800">{section.label}</span>
                <input checked={section.is_enabled} className="h-5 w-5" type="checkbox" onChange={() => toggleSection(section)} />
              </label>
            ))}
          </div>
        </section>

        <section className="rounded-lg border bg-white p-4">
          <h4 className="font-bold text-slate-950">Indicadores visibles</h4>
          <div className="mt-3 grid gap-3">
            {config.sections.map((section) => (
              <div className="rounded border p-3" key={section.section_key}>
                <p className="text-sm font-bold text-slate-700">{section.label}</p>
                <div className="mt-2 grid gap-2">
                  {(widgetsBySection[section.section_key] ?? []).map((widget) => (
                    <label className="flex items-center justify-between gap-3 text-sm" key={widget.widget_key}>
                      <span className="text-slate-700">{widget.label}</span>
                      <input checked={widget.is_enabled} className="h-4 w-4" disabled={!section.is_enabled} type="checkbox" onChange={() => toggleWidget(widget)} />
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {preview ? (
        <section className="rounded-lg border bg-white p-4">
          <h4 className="font-bold text-slate-950">Vista previa como cliente</h4>
          <div className="mt-3 flex flex-wrap gap-2">
            {preview.sections.map((section) => <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-800" key={section.section_key}>{section.label}</span>)}
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {preview.widgets.map((widget) => (
              <div className="rounded border bg-slate-50 p-3" key={widget.widget_key}>
                <p className="text-xs font-semibold uppercase text-slate-500">{widget.section_key}</p>
                <p className="font-bold text-slate-950">{widget.label}</p>
                <p className="mt-1 text-2xl font-black text-emerald-700">{widget.value ?? "-"}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
