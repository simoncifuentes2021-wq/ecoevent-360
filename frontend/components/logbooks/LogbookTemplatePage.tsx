"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Archive, ClipboardCheck, Plus, Trash2 } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { useToast } from "@/components/common/ToastProvider";
import { LogbookDialog } from "@/components/logbooks/LogbookDialog";
import { Button } from "@/components/ui/button";
import { archiveLogbookTemplate, createLogbookTemplate, getLogbookTemplates } from "@/lib/api/logbooks";
import { logbookError } from "@/lib/logbook-errors";
import { logbookEvidencePolicyLabels, logbookItemTypeLabels, logbookLabel, logbookStageLabels, logbookStatusLabels } from "@/lib/logbook-labels";
import type { LogbookTemplate, LogbookTemplateCreate } from "@/types/logbook";

type Section = LogbookTemplateCreate["sections"][number];
const blankItem = () => ({ title: "", position: 0, item_type: "CHECKBOX", is_required: true, allow_not_applicable: false, evidence_policy: "NONE", min_evidences: 0, max_evidences: 5, require_comment_on_failure: false, options: [] });

export function LogbookTemplatePage() {
  const { toast } = useToast();
  const [items, setItems] = useState<LogbookTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editorOpen, setEditorOpen] = useState(false);
  const [archiveTarget, setArchiveTarget] = useState<LogbookTemplate | null>(null);
  const [busy, setBusy] = useState(false);
  const [dialogError, setDialogError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try { setItems((await getLogbookTemplates()).items); }
    catch (reason) { setError(logbookError(reason, "No se pudieron cargar las plantillas.")); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);

  return <div className="space-y-6">
    <PageHeader title="Plantillas de bitácora" description="Procedimientos operativos reutilizables y versionados." actions={<Button onClick={() => setEditorOpen(true)}><Plus className="mr-2 h-4 w-4"/>Nueva plantilla</Button>} />
    {loading ? <LoadingState/> : error ? <ErrorState message={error} onRetry={load}/> : items.length === 0 ? <EmptyState icon={<ClipboardCheck/>} title="No hay plantillas" description="Crea tu primera plantilla operativa."/> : (
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((template) => <article className="rounded-xl border bg-white p-5" key={template.id}>
          <div className="flex items-start justify-between gap-3"><Link className="font-semibold hover:text-emerald-700" href={`/admin/bitacoras/${template.id}`}>{template.name}</Link><span className="rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700">{logbookLabel(logbookStatusLabels, template.status)}</span></div>
          <p className="mt-2 text-sm text-slate-600">{template.description || "Sin descripción"}</p>
          <div className="mt-4 flex items-center justify-between"><p className="text-xs text-slate-500">{template.default_assignment_mode === "SHARED" ? "Compartida" : "Individual"}</p>{template.status !== "ARCHIVED" ? <Button onClick={() => { setDialogError(""); setArchiveTarget(template); }} size="sm" variant="secondary"><Archive className="mr-1 h-4 w-4"/>Archivar</Button> : null}</div>
        </article>)}
      </div>
    )}
    {editorOpen ? <TemplateEditor close={() => setEditorOpen(false)} done={() => { setEditorOpen(false); void load(); toast({ title: "Plantilla creada", description: "La versión 1 quedó como borrador para que puedas revisarla antes de publicar.", tone: "success" }); }}/> : null}
    <LogbookDialog busy={busy} confirmLabel="Archivar plantilla" description={`“${archiveTarget?.name || ""}” dejará de estar disponible para nuevas asignaciones. Las ejecuciones históricas no se eliminarán.`} error={dialogError} onClose={() => setArchiveTarget(null)} onConfirm={async () => {
      if (!archiveTarget || busy) return; setBusy(true); setDialogError("");
      try { await archiveLogbookTemplate(archiveTarget.id); await load(); setArchiveTarget(null); toast({ title: "Plantilla archivada", tone: "success" }); }
      catch (reason) { setDialogError(logbookError(reason, "No se pudo archivar la plantilla.")); }
      finally { setBusy(false); }
    }} open={Boolean(archiveTarget)} title="Archivar plantilla" tone="warning"/>
  </div>;
}

function TemplateEditor({ close, done }: { close: () => void; done: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [stage, setStage] = useState("OPERATION");
  const [mode, setMode] = useState<"INDIVIDUAL" | "SHARED">("INDIVIDUAL");
  const [sections, setSections] = useState<Section[]>([{ title: "General", position: 0, is_required: true, items: [blankItem()] }]);
  const [deleteTarget, setDeleteTarget] = useState<{ section: number; item?: number } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const updateSection = (index: number, patch: Partial<Section>) => setSections((value) => value.map((section, current) => current === index ? { ...section, ...patch } : section));
  const updateItem = (sectionIndex: number, itemIndex: number, patch: Record<string, unknown>) => updateSection(sectionIndex, { items: sections[sectionIndex].items.map((item, current) => current === itemIndex ? { ...item, ...patch } : item) });

  async function submit() {
    if (saving) return; setSaving(true); setError("");
    try {
      await createLogbookTemplate({ name, description, operational_stage: stage, default_assignment_mode: mode, default_client_visibility: false, sections: sections.map((section, sectionIndex) => ({ ...section, position: sectionIndex, items: section.items.map((item, itemIndex) => ({ ...item, position: itemIndex })) })) });
      done();
    } catch (reason) { setError(logbookError(reason, "No se pudo crear la plantilla.")); }
    finally { setSaving(false); }
  }

  function removeTarget() {
    if (!deleteTarget) return;
    if (deleteTarget.item === undefined) setSections((value) => value.filter((_, index) => index !== deleteTarget.section));
    else updateSection(deleteTarget.section, { items: sections[deleteTarget.section].items.filter((_, index) => index !== deleteTarget.item) });
    setDeleteTarget(null);
  }

  const targetName = deleteTarget?.item === undefined ? sections[deleteTarget?.section || 0]?.title : sections[deleteTarget?.section || 0]?.items[deleteTarget?.item || 0]?.title;
  return <ModalShell title="Nueva plantilla de bitácora" description="Configura secciones y tareas. La versión se guardará como borrador." onClose={() => { if (!saving) close(); }}>
    <div className="max-h-[75vh] space-y-4 overflow-y-auto pr-2">
      <label className="grid gap-1 text-sm font-medium">Nombre<input autoFocus className="rounded-xl border p-3" onChange={(event) => setName(event.target.value)} value={name}/></label>
      <label className="grid gap-1 text-sm font-medium">Descripción<textarea className="rounded-xl border p-3" onChange={(event) => setDescription(event.target.value)} value={description}/></label>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2"><label className="grid gap-1 text-sm">Etapa<select className="rounded-xl border p-3" onChange={(event) => setStage(event.target.value)} value={stage}>{Object.entries(logbookStageLabels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="grid gap-1 text-sm">Modalidad<select className="rounded-xl border p-3" onChange={(event) => setMode(event.target.value as typeof mode)} value={mode}><option value="INDIVIDUAL">Individual</option><option value="SHARED">Compartida</option></select></label></div>
      {sections.map((section, sectionIndex) => <section className="rounded-xl border bg-slate-50 p-3" key={sectionIndex}>
        <div className="flex gap-2"><input className="min-w-0 flex-1 rounded-lg border p-2 font-semibold" onChange={(event) => updateSection(sectionIndex, { title: event.target.value })} value={section.title}/><Button disabled={sections.length === 1} onClick={() => setDeleteTarget({ section: sectionIndex })} size="sm" variant="ghost" aria-label={`Eliminar sección ${section.title}`}><Trash2 className="h-4 w-4"/></Button></div>
        <div className="mt-3 space-y-3">{section.items.map((item, itemIndex) => <div className="rounded-lg border bg-white p-3" key={itemIndex}><div className="flex flex-wrap gap-2"><input className="min-w-40 flex-1 rounded-lg border p-2" onChange={(event) => updateItem(sectionIndex, itemIndex, { title: event.target.value })} placeholder="Tarea de bitácora" value={item.title}/><select className="rounded-lg border p-2" onChange={(event) => updateItem(sectionIndex, itemIndex, { item_type: event.target.value })} value={item.item_type}>{Object.entries(logbookItemTypeLabels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select><Button disabled={section.items.length === 1} onClick={() => setDeleteTarget({ section: sectionIndex, item: itemIndex })} size="sm" variant="ghost" aria-label={`Eliminar ítem ${item.title}`}><Trash2 className="h-4 w-4"/></Button></div><div className="mt-2 flex flex-wrap gap-4 text-xs"><label><input checked={item.is_required} onChange={(event) => updateItem(sectionIndex,itemIndex,{is_required:event.target.checked})} type="checkbox"/> Obligatoria</label><label><input checked={item.allow_not_applicable} onChange={(event) => updateItem(sectionIndex,itemIndex,{allow_not_applicable:event.target.checked})} type="checkbox"/> Permitir N/A</label><select className="rounded border" onChange={(event) => updateItem(sectionIndex,itemIndex,{evidence_policy:event.target.value})} value={item.evidence_policy}>{Object.entries(logbookEvidencePolicyLabels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></div></div>)}
          <Button onClick={() => updateSection(sectionIndex, { items: [...section.items, { ...blankItem(), position: section.items.length }] })} size="sm" variant="secondary"><Plus className="h-4 w-4"/>Agregar tarea</Button>
        </div>
      </section>)}
      <Button onClick={() => setSections((value) => [...value, { title: `Sección ${value.length + 1}`, position: value.length, is_required: true, items: [blankItem()] }])} variant="secondary">Agregar sección</Button>
      {error ? <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700" role="alert">{error}</p> : null}
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><Button disabled={saving} onClick={close} variant="secondary">Volver</Button><Button disabled={saving || !name.trim() || sections.some((section) => !section.title.trim() || section.items.some((item) => !item.title.trim()))} onClick={() => void submit()}>{saving ? "Guardando…" : "Crear plantilla"}</Button></div>
    </div>
    <LogbookDialog confirmLabel={deleteTarget?.item === undefined ? "Eliminar sección" : "Eliminar ítem"} description={`“${targetName || "Este elemento"}” y toda su configuración se quitarán del borrador. Esta acción se aplicará al guardar la plantilla.`} onClose={() => setDeleteTarget(null)} onConfirm={removeTarget} open={Boolean(deleteTarget)} title={deleteTarget?.item === undefined ? "Eliminar sección" : "Eliminar ítem"} tone="danger"/>
  </ModalShell>;
}
