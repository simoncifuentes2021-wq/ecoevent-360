"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUp, Eye, Plus, Trash2 } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { LogbookDialog } from "@/components/logbooks/LogbookDialog";
import { Button } from "@/components/ui/button";
import { createLogbookVersion, getLogbookTemplate, getLogbookVersion, publishLogbookVersion, updateLogbookTemplate } from "@/lib/api/logbooks";
import { logbookError } from "@/lib/logbook-errors";
import { logbookEvidencePolicyLabels, logbookItemTypeLabels, logbookLabel, logbookModeLabels, logbookStageLabels, logbookStatusLabels } from "@/lib/logbook-labels";
import type { LogbookItem, LogbookSection, LogbookTemplateDetail, LogbookVersionDetail } from "@/types/logbook";

const types = ["CHECKBOX", "YES_NO", "STATUS_SELECT", "NUMBER", "SHORT_TEXT", "LONG_TEXT", "PHOTO", "CONFIRMATION"] as const;
type DeleteTarget = { section: number; item?: number };

export function TemplateDetailEditor({ id }: { id: string }) {
  const router = useRouter();
  const { toast } = useToast();
  const [template, setTemplate] = useState<LogbookTemplateDetail | null>(null);
  const [version, setVersion] = useState<LogbookVersionDetail | null>(null);
  const [pageError, setPageError] = useState("");
  const [dialogError, setDialogError] = useState("");
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);

  async function load() {
    setPageError("");
    try {
      const current = await getLogbookTemplate(id);
      setTemplate(current);
      const selected = current.versions.find((item) => item.status === "DRAFT") || [...current.versions].sort((a,b) => b.version_number - a.version_number)[0];
      setVersion(selected ? await getLogbookVersion(selected.id) : null);
    } catch (reason) { setPageError(logbookError(reason, "No se pudo cargar la plantilla.")); }
  }
  useEffect(() => { void load(); }, [id]);
  if (pageError) return <ErrorState message={pageError} onRetry={load}/>;
  if (!template || !version) return <LoadingState/>;
  const currentTemplate = template;
  const currentVersion = version;

  const editable = version.status === "DRAFT";
  const setSections = (sections: LogbookSection[]) => setVersion({ ...version, sections: sections.map((section, index) => ({ ...section, position: index, items: section.items.map((item, itemIndex) => ({ ...item, position: itemIndex })) })) });
  const updateItem = (sectionIndex: number, itemIndex: number, patch: Partial<LogbookItem>) => setSections(version.sections.map((section, current) => current === sectionIndex ? { ...section, items: section.items.map((item, index) => index === itemIndex ? { ...item, ...patch } : item) } : section));
  const moveSection = (index: number, direction: number) => { const next = [...version.sections], target = index + direction; if (target < 0 || target >= next.length) return; [next[index], next[target]] = [next[target], next[index]]; setSections(next); };
  const moveItem = (sectionIndex: number, itemIndex: number, direction: number) => { const sections = [...version.sections], items = [...sections[sectionIndex].items], target = itemIndex + direction; if (target < 0 || target >= items.length) return; [items[itemIndex], items[target]] = [items[target], items[itemIndex]]; sections[sectionIndex] = { ...sections[sectionIndex], items }; setSections(sections); };

  async function save(showToast = true) {
    if (saving) return false; setSaving(true); setPageError("");
    try {
      await updateLogbookTemplate(id, { name: currentTemplate.name, description: currentTemplate.description, operational_stage: currentTemplate.operational_stage, default_assignment_mode: currentTemplate.default_assignment_mode, default_client_visibility: currentTemplate.default_client_visibility, sections: currentVersion.sections.map((section) => ({ title: section.title, description: section.description, position: section.position, is_required: section.is_required, items: section.items.map((item) => ({ title: item.title, description: item.description, instructions: item.instructions, position: item.position, item_type: item.item_type, is_required: item.is_required, allow_not_applicable: item.allow_not_applicable, evidence_policy: item.evidence_policy, min_evidences: item.min_evidences, max_evidences: item.max_evidences, require_comment_on_failure: item.require_comment_on_failure, options: item.options.map((option) => ({ label: option.label, value: option.value, position: option.position, is_success_value: option.is_success_value, is_failure_value: option.is_failure_value })) })) })) });
      await load(); if (showToast) toast({ title: "Borrador guardado", tone: "success" }); return true;
    } catch (reason) { setPageError(logbookError(reason, "No se pudo guardar el borrador.")); return false; }
    finally { setSaving(false); }
  }

  async function publish() {
    if (saving) return; setSaving(true); setDialogError("");
    try {
      await updateLogbookTemplate(id, { name: currentTemplate.name, description: currentTemplate.description, operational_stage: currentTemplate.operational_stage, default_assignment_mode: currentTemplate.default_assignment_mode, default_client_visibility: currentTemplate.default_client_visibility, sections: currentVersion.sections.map((section) => ({ title: section.title, description: section.description, position: section.position, is_required: section.is_required, items: section.items.map((item) => ({ title: item.title, description: item.description, instructions: item.instructions, position: item.position, item_type: item.item_type, is_required: item.is_required, allow_not_applicable: item.allow_not_applicable, evidence_policy: item.evidence_policy, min_evidences: item.min_evidences, max_evidences: item.max_evidences, require_comment_on_failure: item.require_comment_on_failure, options: item.options.map((option) => ({ label: option.label, value: option.value, position: option.position, is_success_value: option.is_success_value, is_failure_value: option.is_failure_value })) })) })) });
      await publishLogbookVersion(currentVersion.id); await load(); setPublishOpen(false); toast({ title: "Versión publicada", tone: "success" });
    } catch (reason) { setDialogError(logbookError(reason, "No se pudo publicar la versión.")); }
    finally { setSaving(false); }
  }

  function remove() {
    if (!deleteTarget) return;
    if (deleteTarget.item === undefined) setSections(currentVersion.sections.filter((_, index) => index !== deleteTarget.section));
    else setSections(currentVersion.sections.map((section, index) => index === deleteTarget.section ? { ...section, items: section.items.filter((_, itemIndex) => itemIndex !== deleteTarget.item) } : section));
    setDeleteTarget(null);
  }
  const targetName = deleteTarget?.item === undefined ? version.sections[deleteTarget?.section || 0]?.title : version.sections[deleteTarget?.section || 0]?.items[deleteTarget?.item || 0]?.title;

  return <div className="space-y-5">
    <Button onClick={() => router.back()} variant="ghost">Volver</Button>
    <div className="rounded-2xl border bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><input className="max-w-full text-2xl font-bold outline-none" disabled={!editable} onChange={(event) => setTemplate({ ...template, name: event.target.value })} value={template.name}/><p className="text-sm text-slate-500">Versión {version.version_number} · {logbookLabel(logbookStatusLabels, version.status)}</p></div>
        <div className="flex flex-wrap gap-2"><Button onClick={() => setPreview(!preview)} variant="secondary"><Eye className="h-4 w-4"/>Vista previa</Button>{!editable && template.status !== "ARCHIVED" ? <Button disabled={saving} onClick={async () => { if (saving) return; setSaving(true); try { await createLogbookVersion(id,version.id); await load(); toast({title:"Nueva versión creada",tone:"success"}); } catch(reason){setPageError(logbookError(reason));} finally{setSaving(false);} }}>Nueva versión</Button> : null}{editable ? <Button disabled={saving} onClick={() => void save()}>{saving ? "Guardando…" : "Guardar borrador"}</Button> : null}{editable ? <Button disabled={saving} onClick={() => { setDialogError(""); setPublishOpen(true); }}>Publicar</Button> : null}</div>
      </div>
      <textarea className="mt-3 w-full rounded-xl border p-3" disabled={!editable} onChange={(event) => setTemplate({ ...template, description: event.target.value })} value={template.description || ""}/>
      <div className="mt-3 grid gap-3 md:grid-cols-3"><label className="grid gap-1 text-sm">Etapa<select className="rounded-xl border p-3" disabled={!editable} onChange={(event) => setTemplate({ ...template, operational_stage: event.target.value })} value={template.operational_stage}>{Object.entries(logbookStageLabels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="grid gap-1 text-sm">Modalidad predeterminada<select className="rounded-xl border p-3" disabled={!editable} onChange={(event) => setTemplate({ ...template, default_assignment_mode: event.target.value as typeof template.default_assignment_mode })} value={template.default_assignment_mode}>{Object.entries(logbookModeLabels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="flex items-center gap-2 pt-6 text-sm"><input checked={template.default_client_visibility} disabled={!editable} onChange={(event) => setTemplate({ ...template, default_client_visibility: event.target.checked })} type="checkbox"/>Visible para cliente por defecto</label></div>
      <div className="mt-3 flex flex-wrap gap-2">{template.versions.slice().sort((a,b) => b.version_number-a.version_number).map((item) => <Button key={item.id} onClick={async () => setVersion(await getLogbookVersion(item.id))} size="sm" variant={item.id === version.id ? "primary" : "secondary"}>v{item.version_number} · {logbookLabel(logbookStatusLabels,item.status)}</Button>)}</div>
    </div>

    {preview ? <Preview sections={version.sections}/> : <div className="space-y-4">{version.sections.map((section, sectionIndex) => <section className="rounded-2xl border bg-white p-4" key={section.id || sectionIndex}>
      <div className="flex gap-2"><input className="min-w-0 flex-1 rounded-lg border p-2 font-semibold" disabled={!editable} onChange={(event) => setSections(version.sections.map((value,index) => index === sectionIndex ? { ...value,title:event.target.value } : value))} value={section.title}/>{editable ? <><Button onClick={() => moveSection(sectionIndex,-1)} size="sm" variant="ghost"><ArrowUp className="h-4 w-4"/></Button><Button onClick={() => moveSection(sectionIndex,1)} size="sm" variant="ghost"><ArrowDown className="h-4 w-4"/></Button><Button onClick={() => setDeleteTarget({section:sectionIndex})} size="sm" variant="ghost" aria-label={`Eliminar sección ${section.title}`}><Trash2 className="h-4 w-4"/></Button></> : null}</div>
      <div className="mt-3 space-y-3">{section.items.map((item,itemIndex) => <div className="rounded-xl border bg-slate-50 p-3" key={item.id || itemIndex}><div className="flex flex-wrap gap-2"><input className="min-w-40 flex-1 rounded-lg border p-2" disabled={!editable} onChange={(event) => updateItem(sectionIndex,itemIndex,{title:event.target.value})} value={item.title}/><select className="rounded-lg border p-2" disabled={!editable} onChange={(event) => updateItem(sectionIndex,itemIndex,{item_type:event.target.value as LogbookItem["item_type"]})} value={item.item_type}>{types.map((type) => <option key={type} value={type}>{logbookLabel(logbookItemTypeLabels,type)}</option>)}</select>{editable ? <><Button onClick={() => moveItem(sectionIndex,itemIndex,-1)} size="sm" variant="ghost"><ArrowUp className="h-4 w-4"/></Button><Button onClick={() => moveItem(sectionIndex,itemIndex,1)} size="sm" variant="ghost"><ArrowDown className="h-4 w-4"/></Button><Button onClick={() => setDeleteTarget({section:sectionIndex,item:itemIndex})} size="sm" variant="ghost" aria-label={`Eliminar ítem ${item.title}`}><Trash2 className="h-4 w-4"/></Button></> : null}</div><div className="mt-2 flex flex-wrap gap-3 text-xs"><label><input checked={item.is_required} disabled={!editable} onChange={(event) => updateItem(sectionIndex,itemIndex,{is_required:event.target.checked})} type="checkbox"/> Obligatoria</label><label><input checked={item.allow_not_applicable} disabled={!editable} onChange={(event) => updateItem(sectionIndex,itemIndex,{allow_not_applicable:event.target.checked})} type="checkbox"/> N/A</label><select disabled={!editable} onChange={(event) => updateItem(sectionIndex,itemIndex,{evidence_policy:event.target.value})} value={item.evidence_policy}>{Object.entries(logbookEvidencePolicyLabels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></div></div>)}
        {editable ? <Button onClick={() => setSections(version.sections.map((value,index) => index === sectionIndex ? { ...value,items:[...value.items,{id:`new-${Date.now()}`,title:"Nueva tarea",position:value.items.length,item_type:"CHECKBOX",is_required:true,allow_not_applicable:false,evidence_policy:"NONE",min_evidences:0,max_evidences:5,require_comment_on_failure:false,requires_supervisor_review:false,client_visible_by_default:false,creates_incident_suggestion:false,options:[]}]} : value))} size="sm" variant="secondary"><Plus className="h-4 w-4"/>Ítem</Button> : null}
      </div>
    </section>)}{editable ? <Button onClick={() => setSections([...version.sections,{id:`new-${Date.now()}`,title:"Nueva sección",position:version.sections.length,is_required:true,items:[]}])} variant="secondary"><Plus className="h-4 w-4"/>Sección</Button> : null}</div>}

    <LogbookDialog busy={saving} confirmLabel="Publicar versión" description="Después de publicarla, esta versión quedará disponible para crear bitácoras y ya no podrá editarse." error={dialogError} onClose={() => setPublishOpen(false)} onConfirm={() => void publish()} open={publishOpen} title="Publicar versión de la plantilla"/>
    <LogbookDialog confirmLabel={deleteTarget?.item === undefined ? "Eliminar sección" : "Eliminar ítem"} description={`“${targetName || "Este elemento"}” y todo su contenido configurado se quitarán del borrador al guardar.`} onClose={() => setDeleteTarget(null)} onConfirm={remove} open={Boolean(deleteTarget)} title={deleteTarget?.item === undefined ? "Eliminar sección" : "Eliminar ítem"} tone="danger"/>
  </div>;
}

function Preview({ sections }: { sections: LogbookSection[] }) { return <div className="mx-auto max-w-2xl space-y-4 rounded-2xl border bg-slate-50 p-5">{sections.map((section) => <section className="rounded-xl bg-white p-4" key={section.id}><h2 className="font-semibold">{section.title}</h2>{section.items.map((item) => <p className="mt-3 border-t pt-3 text-sm" key={item.id}>{item.title}{item.is_required ? " *" : ""} <span className="text-slate-400">· {logbookLabel(logbookItemTypeLabels,item.item_type)}</span></p>)}</section>)}</div>; }
