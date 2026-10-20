"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, Check, LoaderCircle, Users } from "lucide-react";

import { ModalShell } from "@/components/common/ModalShell";
import { useToast } from "@/components/common/ToastProvider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  documentApi,
  type DocumentPerson,
  type ExistingPersonAssignment,
} from "@/lib/api/documents";
import type { Event } from "@/types/event";

type Employment = {
  id?: string;
  event_id: string | null;
  position: string;
  area: string | null;
  workplace: string | null;
  start_date: string | null;
  end_date: string | null;
  remuneration: string | null;
};
type AssignmentDraft = Omit<ExistingPersonAssignment, "person_id">;
type BulkFields = Omit<AssignmentDraft, "position">;

function employmentOf(person: DocumentPerson): Employment | null {
  const value = person.latest_employment;
  if (!value || typeof value !== "object") return null;
  const row = value as Record<string, unknown>;
  return {
    id: typeof row.id === "string" ? row.id : undefined,
    event_id: typeof row.event_id === "string" ? row.event_id : null,
    position: typeof row.position === "string" ? row.position : "",
    area: typeof row.area === "string" ? row.area : null,
    workplace: typeof row.workplace === "string" ? row.workplace : null,
    start_date: typeof row.start_date === "string" ? row.start_date.slice(0, 10) : null,
    end_date: typeof row.end_date === "string" ? row.end_date.slice(0, 10) : null,
    remuneration: row.remuneration == null ? null : String(row.remuneration),
  };
}

function queryParams(clientId: string) {
  return clientId ? `?client_id=${encodeURIComponent(clientId)}` : "";
}

const fieldClass = "grid gap-1 text-xs font-medium text-slate-700";

export function AssignExistingPeopleModal({
  events,
  clientId,
  open,
  onClose,
  onDone,
}: {
  events: Event[];
  clientId: string;
  open: boolean;
  onClose: () => void;
  onDone: () => Promise<void>;
}) {
  const { toast } = useToast();
  const [sourceEventId, setSourceEventId] = useState("");
  const [targetEventId, setTargetEventId] = useState("");
  const [sourcePeople, setSourcePeople] = useState<DocumentPerson[]>([]);
  const [targetPeople, setTargetPeople] = useState<DocumentPerson[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [drafts, setDrafts] = useState<Record<string, AssignmentDraft>>({});
  const [bulkFields, setBulkFields] = useState<BulkFields>({ area: "", workplace: "", start_date: "", end_date: "", remuneration: "" });
  const [applyBulkPosition, setApplyBulkPosition] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [generateDocuments, setGenerateDocuments] = useState(false);
  const [loadingSource, setLoadingSource] = useState(false);
  const [loadingTarget, setLoadingTarget] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!open) return;
    setSourceEventId("");
    setTargetEventId("");
    setSourcePeople([]);
    setTargetPeople([]);
    setSelectedIds([]);
    setDrafts({});
    setBulkFields({ area: "", workplace: "", start_date: "", end_date: "", remuneration: "" });
    setApplyBulkPosition("");
    setExpandedId(null);
    setSearch("");
    setGenerateDocuments(false);
    setLoadError("");
  }, [open]);

  useEffect(() => {
    if (!open || !sourceEventId) {
      setSourcePeople([]);
      setSelectedIds([]);
      setDrafts({});
      return;
    }
    let active = true;
    setLoadingSource(true);
    setLoadError("");
    documentApi.people(`${queryParams(clientId)}${clientId ? "&" : "?"}event_id=${encodeURIComponent(sourceEventId)}`)
      .then((rows) => {
        if (!active) return;
        setSourcePeople(rows);
        setSelectedIds([]);
        setDrafts(Object.fromEntries(rows.map((person) => {
          const previous = employmentOf(person);
          return [person.id, {
            position: previous?.position || "",
            area: previous?.area || "",
            workplace: previous?.workplace || "",
            // Dates and pay are event-specific; require the admin to confirm them rather than copying old values.
            start_date: "",
            end_date: "",
            remuneration: "",
          }];
        })));
      })
      .catch((cause) => { if (active) setLoadError(cause instanceof Error ? cause.message : "No se pudo cargar el personal de origen."); })
      .finally(() => { if (active) setLoadingSource(false); });
    return () => { active = false; };
  }, [open, sourceEventId, clientId]);

  useEffect(() => {
    if (!open || !targetEventId) {
      setTargetPeople([]);
      return;
    }
    let active = true;
    setLoadingTarget(true);
    documentApi.people(`${queryParams(clientId)}${clientId ? "&" : "?"}event_id=${encodeURIComponent(targetEventId)}`)
      .then((rows) => { if (active) setTargetPeople(rows); })
      .catch((cause) => { if (active) setLoadError(cause instanceof Error ? cause.message : "No se pudo comprobar el personal de destino."); })
      .finally(() => { if (active) setLoadingTarget(false); });
    return () => { active = false; };
  }, [open, targetEventId, clientId]);

  const alreadyAssigned = useMemo(() => new Set(targetPeople.map((person) => person.id)), [targetPeople]);
  const eligiblePeople = useMemo(() => sourcePeople.filter((person) => !alreadyAssigned.has(person.id)), [sourcePeople, alreadyAssigned]);
  const filteredPeople = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("es-CL");
    return sourcePeople.filter((person) => !needle || `${person.first_name} ${person.last_name} ${person.rut}`.toLocaleLowerCase("es-CL").includes(needle));
  }, [sourcePeople, search]);
  const selectedPeople = useMemo(() => eligiblePeople.filter((person) => selectedIds.includes(person.id)), [eligiblePeople, selectedIds]);
  const eventsById = useMemo(() => new Map(events.map((event) => [event.id, event])), [events]);

  function togglePerson(personId: string) {
    if (alreadyAssigned.has(personId)) return;
    setSelectedIds((current) => current.includes(personId) ? current.filter((id) => id !== personId) : [...current, personId]);
  }

  function updateDraft(personId: string, key: keyof AssignmentDraft, value: string) {
    setDrafts((current) => ({ ...current, [personId]: { ...current[personId], [key]: value } }));
  }

  function applyCommonValues() {
    const hasBulkValues = Boolean(applyBulkPosition.trim() || Object.values(bulkFields).some(Boolean));
    if (!hasBulkValues) return;
    setDrafts((current) => {
      const next = { ...current };
      selectedIds.forEach((id) => {
        if (alreadyAssigned.has(id)) return;
        next[id] = {
          ...next[id],
          ...(applyBulkPosition.trim() ? { position: applyBulkPosition.trim() } : {}),
          ...Object.fromEntries(Object.entries(bulkFields).filter(([, value]) => Boolean(value))),
        };
      });
      return next;
    });
      toast({ title: "Datos aplicados", description: "Se aplicaron a las personas seleccionadas; puedes ajustar excepciones por persona.", tone: "success" });
  }

  async function submit() {
    if (!sourceEventId || !targetEventId || selectedPeople.length === 0) return;
    const invalid = selectedPeople.find((person) => !drafts[person.id]?.position?.trim());
    if (invalid) {
      toast({ title: "Falta el cargo", description: `Completa el cargo de ${invalid.first_name} ${invalid.last_name}.`, tone: "error" });
      setExpandedId(invalid.id);
      return;
    }
    setBusy(true);
    try {
      const result = await documentApi.assignExisting({
        source_event_id: sourceEventId,
        target_event_id: targetEventId,
        generate_documents: generateDocuments,
        assignments: selectedPeople.map((person) => ({ person_id: person.id, ...drafts[person.id] })),
      });
      const descriptions = [
        `${result.assigned.length} personas asignadas a ${result.target_event_name}.`,
        result.already_assigned.length ? `${result.already_assigned.length} ya estaban asignadas y se omitieron.` : "",
        generateDocuments ? `${result.contracts_created} contratos y ${result.epp_documents_created} registros EPP creados como borradores; no se enviaron correos.` : "No se generaron ni enviaron documentos.",
        result.setup_warnings.length ? `Faltan datos base: ${result.setup_warnings.join(", ")}.` : "",
      ].filter(Boolean).join(" ");
      toast({ title: "Asignación masiva completada", description: descriptions, tone: "success" });
      if (result.already_assigned.length) {
        toast({ title: "Personas omitidas", description: result.already_assigned.map((person) => `${person.name} (${person.rut})`).join(" · "), tone: "error" });
      }
      onClose();
      await onDone();
    } catch (cause) {
      toast({ title: "No se pudo asignar el personal", description: cause instanceof Error ? cause.message : "Revisa los datos y vuelve a intentarlo.", tone: "error" });
    } finally { setBusy(false); }
  }

  if (!open) return null;

  return <ModalShell size="lg" title="Asignar personal de otra faena" description="Reutiliza las fichas existentes. El historial y los documentos de la faena anterior se mantienen intactos." onClose={() => { if (!busy) onClose(); }}>
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1.5 text-sm font-medium text-slate-700">Faena de origen<select className="h-10 rounded-md border bg-white px-3" value={sourceEventId} disabled={busy} onChange={(event) => setSourceEventId(event.target.value)}><option value="">Selecciona de dónde vienen</option>{events.map((event) => <option key={event.id} value={event.id} disabled={event.id === targetEventId}>{event.name}</option>)}</select></label>
        <label className="grid gap-1.5 text-sm font-medium text-slate-700">Faena de destino<select className="h-10 rounded-md border bg-white px-3" value={targetEventId} disabled={busy} onChange={(event) => setTargetEventId(event.target.value)}><option value="">Selecciona dónde trabajarán</option>{events.map((event) => <option key={event.id} value={event.id} disabled={event.id === sourceEventId}>{event.name}</option>)}</select></label>
      </div>
      {sourceEventId && targetEventId && <p className="flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-900"><span className="font-semibold">{eventsById.get(sourceEventId)?.name}</span><ArrowRight className="h-4 w-4 shrink-0"/><span className="font-semibold">{eventsById.get(targetEventId)?.name}</span></p>}

      {sourceEventId && targetEventId && <>
        {alreadyAssigned.size > 0 && <div role="status" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"><p className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4"/>Personal que ya está en la faena de destino</p><p className="mt-1">{sourcePeople.filter((person) => alreadyAssigned.has(person.id)).length} persona(s) de esta selección ya estaban asignadas. Se muestran deshabilitadas y el servidor volverá a comprobarlo al confirmar.</p></div>}
        <div className="flex flex-wrap items-center gap-2"><label className="min-w-48 flex-1"><span className="sr-only">Buscar trabajador</span><Input placeholder="Buscar por nombre o RUT" value={search} onChange={(event) => setSearch(event.target.value)}/></label><Button type="button" variant="secondary" size="sm" disabled={eligiblePeople.length === 0} onClick={() => setSelectedIds((current) => current.length === eligiblePeople.length ? [] : eligiblePeople.map((person) => person.id))}>{selectedIds.length === eligiblePeople.length && eligiblePeople.length ? "Quitar selección" : "Seleccionar disponibles"}</Button><span className="text-xs text-slate-500">{selectedIds.length} seleccionados</span></div>

        {loadingSource || loadingTarget ? <p className="flex items-center gap-2 py-5 text-sm text-slate-500"><LoaderCircle className="h-4 w-4 animate-spin"/>Comprobando personas y asignaciones…</p> : loadError ? <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{loadError}</p> : sourcePeople.length === 0 ? <p className="rounded-lg border border-dashed p-5 text-center text-sm text-slate-500">No hay personal registrado en la faena de origen.</p> : <div className="max-h-64 space-y-2 overflow-y-auto rounded-lg border p-2">{filteredPeople.map((person) => {
          const duplicate = alreadyAssigned.has(person.id);
          const chosen = selectedIds.includes(person.id);
          const employment = employmentOf(person);
          return <div className={`rounded-lg border p-3 ${duplicate ? "border-amber-200 bg-amber-50/60" : chosen ? "border-emerald-300 bg-emerald-50/50" : "bg-white"}`} key={person.id}>
            <div className="flex items-center gap-3"><input aria-label={`Seleccionar a ${person.first_name} ${person.last_name}`} type="checkbox" checked={chosen} disabled={busy || duplicate} onChange={() => togglePerson(person.id)}/><div className="min-w-0 flex-1"><p className="font-semibold text-slate-900">{person.first_name} {person.last_name} <span className="font-normal text-slate-500">· {person.rut}</span></p><p className="text-xs text-slate-500">Origen: {employment?.position || "Cargo sin datos"}{employment?.area ? ` · ${employment.area}` : ""}{duplicate ? " · Ya asignada al destino" : ""}</p></div>{chosen && <button type="button" className="text-xs font-semibold text-emerald-800 underline" onClick={() => setExpandedId((current) => current === person.id ? null : person.id)}>{expandedId === person.id ? "Ocultar ajustes" : "Ajustar datos"}</button>}</div>
            {chosen && expandedId === person.id && <div className="mt-3 grid gap-2 border-t pt-3 sm:grid-cols-3">{([ ["position", "Cargo / funciones", true], ["area", "Área", false], ["workplace", "Lugar de trabajo", false], ["start_date", "Fecha de inicio", false], ["end_date", "Fecha de término", false], ["remuneration", "Remuneración", false] ] as Array<[keyof AssignmentDraft, string, boolean]>).map(([key, label, required]) => <label className={fieldClass} key={key}>{label}<Input required={required} type={key === "start_date" || key === "end_date" ? "date" : key === "remuneration" ? "number" : "text"} value={String(drafts[person.id]?.[key] || "")} onChange={(event) => updateDraft(person.id, key, event.target.value)}/></label>)}</div>}
          </div>;
        })}</div>}

        {selectedPeople.length > 0 && <details className="rounded-lg border bg-slate-50 p-3"><summary className="cursor-pointer text-sm font-semibold text-slate-800">Aplicar datos comunes a los {selectedPeople.length} seleccionados</summary><p className="mt-2 text-xs text-slate-600">Solo se reemplazan los campos que completes. Luego puedes ajustar cada excepción individual.</p><div className="mt-3 grid gap-2 sm:grid-cols-3"><label className={fieldClass}>Cargo / funciones<Input value={applyBulkPosition} onChange={(event) => setApplyBulkPosition(event.target.value)} placeholder="Se conserva el cargo de origen si lo dejas vacío"/></label>{([ ["area", "Área"], ["workplace", "Lugar de trabajo"], ["start_date", "Fecha de inicio"], ["end_date", "Fecha de término"], ["remuneration", "Remuneración"] ] as Array<[keyof BulkFields, string]>).map(([key, label]) => <label className={fieldClass} key={key}>{label}<Input type={key === "start_date" || key === "end_date" ? "date" : key === "remuneration" ? "number" : "text"} value={String(bulkFields[key] || "")} onChange={(event) => setBulkFields((current) => ({ ...current, [key]: event.target.value }))}/></label>)}</div><div className="mt-3 flex justify-end"><Button type="button" size="sm" variant="secondary" onClick={applyCommonValues}>Aplicar a seleccionados</Button></div></details>}

        <label className="flex items-start gap-2 rounded-lg border p-3 text-sm"><input className="mt-1" type="checkbox" checked={generateDocuments} onChange={(event) => setGenerateDocuments(event.target.checked)} disabled={busy}/><span><strong className="block">Generar contrato y registro EPP como borradores</strong><span className="text-xs text-slate-600">Opcional. No se enviará ningún correo. Los documentos existentes no se duplican; el trabajador completará el EPP cuando se envíe.</span></span></label>
      </>}

      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-4"><p className="flex items-center gap-2 text-xs text-slate-500"><Users className="h-4 w-4"/>La asignación anterior y sus documentos no se modifican.</p><div className="flex gap-2"><Button type="button" variant="secondary" disabled={busy} onClick={onClose}>Cerrar</Button><Button type="button" disabled={busy || loadingSource || loadingTarget || !sourceEventId || !targetEventId || selectedPeople.length === 0} onClick={() => void submit()}>{busy ? <><LoaderCircle className="h-4 w-4 animate-spin"/>Asignando…</> : <><Check className="h-4 w-4"/>{generateDocuments ? `Asignar y generar borradores` : `Asignar ${selectedPeople.length} personas`}</>}</Button></div></div>
    </div>
  </ModalShell>;
}
