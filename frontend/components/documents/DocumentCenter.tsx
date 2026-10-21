"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { ChevronDown, ChevronLeft, ChevronRight, Clipboard, Download, FileCheck2, FilePlus2, FileText, LoaderCircle, Pencil, Plus, Printer, Search, ShieldCheck, Upload, Users } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { useToast } from "@/components/common/ToastProvider";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { useAuth } from "@/hooks/useAuth";
import { documentApi, publicPreview, type DocumentContractDefaults, type DocumentEmailBatch, type DocumentHistoryEntry, type DocumentPairSendResult, type DocumentPerson, type DocumentSummary, type DraftGenerationPreview, type DocumentBatchGenerationResult, type ManagedDocument, type MissingDraftGenerationResult, type PeopleImportResult, type SignatureLink } from "@/lib/api/documents";
import { getClients } from "@/lib/api/clients";
import { getEvents } from "@/lib/api/events";
import type { Client } from "@/types/client";
import type { Event } from "@/types/event";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { AssignExistingPeopleModal } from "@/components/documents/AssignExistingPeopleModal";
import { RepresentativeSignatureSettings } from "@/components/documents/RepresentativeSignatureSettings";
import { PaperPrintBatchModal } from "@/components/documents/PaperPrintBatchModal";
import { PaperDocumentActions } from "@/components/documents/PaperDocumentActions";

type ImportPreview = { valid_rows: Record<string, unknown>[]; errors: Array<{ row: number; field: string; message: string }>; total_rows: number; valid_count: number; error_count: number };
type ItemDraft = { item_code: string; label: string; received_at: string; returned_at: string; received_conformity: boolean };
type EmploymentSummary = { id: string; event_id: string | null; position: string; duties: string | null; area: string | null; workplace: string | null; start_date: string | null; end_date: string | null; remuneration: string | null };
const DOCUMENT_EMAIL_BATCH_STORAGE_KEY = "greenway.documents.active-email-batch";

function getEmploymentSummary(person: DocumentPerson): EmploymentSummary | null {
  const value = person.latest_employment;
  if (!value || typeof value.id !== "string") return null;
  return {
    id: value.id,
    event_id: typeof value.event_id === "string" ? value.event_id : null,
    position: typeof value.position === "string" ? value.position : "",
    duties: typeof value.duties === "string" ? value.duties : null,
    area: typeof value.area === "string" ? value.area : null,
    workplace: typeof value.workplace === "string" ? value.workplace : null,
    start_date: typeof value.start_date === "string" ? value.start_date.slice(0, 10) : null,
    end_date: typeof value.end_date === "string" ? value.end_date.slice(0, 10) : null,
    remuneration: value.remuneration == null ? null : String(value.remuneration),
  };
}

const CATALOG: ItemDraft[] = [
  ["JOCKEY", "Jockey"], ["GLOVES", "Guantes"], ["UV_SHIRT", "Polera con filtro UV"],
  ["REFLECTIVE_VEST", "Chaleco reflectante"], ["GOGGLES", "Antiparras"],
  ["SUNSCREEN", "Bloqueador solar"], ["WATER", "Agua"], ["EAR_PROTECTION", "Protectores auditivos"],
].map(([item_code, label]) => ({ item_code, label, received_at: "", returned_at: "", received_conformity: false }));

const fieldClass = "grid gap-1.5 text-sm font-medium text-slate-700";
const EMPTY_CONTRACT_DEFAULTS: DocumentContractDefaults = { employer_name: "", employer_rut: "", representative_name: "", representative_rut: "", employer_address: "", employer_commune: "Santiago" };
const statuses: Record<string, string> = { DRAFT: "Borrador", READY: "Listo", SENT: "Enviado", VIEWED: "Revisado", PARTIALLY_SIGNED: "Firma pendiente", COMPLETED: "Completado", CANCELLED: "Cancelado", EXPIRED: "Vencido", SUPERSEDED: "Reemplazado" };
const paperStatusClasses: Record<string, string> = {
  PREPARED: "bg-sky-100 text-sky-900",
  PRINTED: "bg-amber-100 text-amber-900",
  SIGNED_RECEIVED: "bg-emerald-100 text-emerald-900",
  ARCHIVED: "bg-violet-100 text-violet-900",
};
const historyActionLabels: Record<string, string> = {
  DOCUMENT_MISSING_DRAFTS_WORKER_PROCESSED: "Se revisaron los documentos pendientes de esta persona",
  DOCUMENT_BATCH_WORKER_PROCESSED: "Se procesó esta persona durante la importación",
  DOCUMENT_PERSON_IMPORTED: "Se importaron los datos de esta persona",
  DOCUMENT_PERSON_CREATED: "Se creó la ficha de esta persona",
  DOCUMENT_PERSON_UPDATED: "Se actualizaron los datos de esta persona",
  DOCUMENT_EMPLOYMENT_UPDATED: "Se actualizaron los datos de trabajo para esta faena",
  DOCUMENT_CREATED: "Se creó un documento borrador",
  DOCUMENT_UPDATED: "Se modificó un documento",
  DOCUMENT_PREPARED: "Se preparó el documento para firma",
  DOCUMENT_SENT_FOR_SIGNATURE: "Se envió el documento para firma",
  DOCUMENT_SENT_WITH_CONTRACT_BUNDLE: "Se enviaron juntos el contrato y el registro EPP",
  DOCUMENT_COMPLETED: "Se completó la firma del documento",
  DOCUMENT_CANCELLED: "Se canceló el documento",
  DOCUMENT_VERSION_CREATED: "Se creó una nueva versión del documento",
  DOCUMENT_SIGNED_COPY_SENT: "Se reenviaron los documentos firmados por correo",
  DOCUMENT_PAPER_PRINT_BATCH_PREPARED: "Se preparó un lote para firma en papel",
  DOCUMENT_PAPER_PRINT_SINGLE_PREPARED: "Se preparó este documento para firma en papel",
  DOCUMENT_PAPER_BATCH_PRINTED: "Se registró la impresión de un lote en papel",
  DOCUMENT_PAPER_SIGNED_RECEIVED: "Se registró la recepción del documento firmado en papel",
  DOCUMENT_PAPER_SIGNED_COPY_ARCHIVED: "Se archivó la copia firmada en papel",
  DOCUMENT_REPRESENTATIVE_SIGNATURE_UPDATED: "Se actualizó la firma del representante legal",
  DOCUMENT_REPRESENTATIVE_SIGNATURE_DELETED: "Se eliminó la firma guardada del representante legal",
};
const historyFieldLabels: Record<string, string> = {
  first_name: "Nombre", last_name: "Apellidos", email: "Correo", phone: "Teléfono",
  address: "Domicilio", commune: "Comuna", position: "Cargo", duties: "Funciones",
  area: "Área", workplace: "Lugar de trabajo", start_date: "Fecha de inicio",
  end_date: "Fecha de término", remuneration: "Remuneración", title: "Documento",
  status: "Estado", kind: "Tipo de documento", created: "Documentos creados",
  already_had: "Documentos que ya tenía", documents_created: "Documentos creados",
  documents_skipped: "Documentos omitidos", workers_processed: "Personas procesadas",
  file_name: "Archivo", recipient: "Destinatario", email_sent: "Correo enviado",
  document_count: "Cantidad de documentos", page_count: "Páginas",
};

function historyValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => historyValue(item)).join(", ") || "Ninguno";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (value == null || value === "") return "—";
  const text = String(value);
  const labels: Record<string, string> = { CONTRACT: "Contrato", EPP: "Registro EPP / RIOHS / EIRL", DRAFT: "Borrador", READY: "Listo", SENT: "Enviado", VIEWED: "Revisado", COMPLETED: "Completado", CANCELLED: "Cancelado", PREPARED: "Preparado para papel", PRINTED: "Impreso", SIGNED_RECEIVED: "Firma recibida", ARCHIVED: "Copia archivada" };
  return labels[text] || text;
}

function historyDetails(entry: DocumentHistoryEntry): Array<{ label: string; value: string }> {
  const details: Array<{ label: string; value: string }> = [];
  const metadata = entry.metadata || {};
  for (const key of ["created", "already_had", "documents_created", "documents_skipped", "workers_processed", "document_count", "page_count", "kind", "status", "email_sent", "file_name"]) {
    if (key in metadata && historyFieldLabels[key]) details.push({ label: historyFieldLabels[key], value: historyValue(metadata[key]) });
  }
  if (entry.old_data && entry.new_data) {
    for (const key of Array.from(new Set([...Object.keys(entry.old_data), ...Object.keys(entry.new_data)]))) {
      const before = entry.old_data[key]; const after = entry.new_data[key];
      if (JSON.stringify(before) !== JSON.stringify(after) && historyFieldLabels[key]) {
        details.push({ label: historyFieldLabels[key], value: `${historyValue(before)} → ${historyValue(after)}` });
      }
    }
  }
  return details;
}

function qs(values: Record<string, string | undefined>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, value); });
  const text = params.toString(); return text ? `?${text}` : "";
}

export function DocumentCenter({ supervisor = false }: { supervisor?: boolean }) {
  const { user } = useAuth();
  const { toast } = useToast();
  const isAdmin = user?.role === "ADMIN" || user?.role === "SUPER_ADMIN";
  const [clients, setClients] = useState<Client[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [clientId, setClientId] = useState(user?.client_id || "");
  const [eventId, setEventId] = useState("");
  const [people, setPeople] = useState<DocumentPerson[]>([]);
  const [documents, setDocuments] = useState<ManagedDocument[]>([]);
  const [summary, setSummary] = useState<DocumentSummary>({ people: 0, documents: 0, pending: 0, completed: 0, incomplete_epp: 0 });
  const [contractDefaults, setContractDefaults] = useState<DocumentContractDefaults>(EMPTY_CONTRACT_DEFAULTS);
  const [eventContractDefaults, setEventContractDefaults] = useState<DocumentContractDefaults>(EMPTY_CONTRACT_DEFAULTS);
  const [savingEventContractDefaults, setSavingEventContractDefaults] = useState(false);
  const [applyingEmployerDefaults, setApplyingEmployerDefaults] = useState(false);
  const [confirmApplyEmployerDefaults, setConfirmApplyEmployerDefaults] = useState(false);
  const [positionFilter, setPositionFilter] = useState("");
  const [historyPerson, setHistoryPerson] = useState<{ id: string; name: string; eventId: string } | null>(null);
  const [historyEntries, setHistoryEntries] = useState<DocumentHistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [eventEppItems, setEventEppItems] = useState<Array<{ item_code: string; label: string }>>(CATALOG.map(({ item_code, label }) => ({ item_code, label })));
  const [editingEppItems, setEditingEppItems] = useState<Array<{ item_code: string; label: string }>>([]);
  const [eppTemplateOpen, setEppTemplateOpen] = useState(false);
  const [savingEppTemplate, setSavingEppTemplate] = useState(false);
  const [savingContractDefaults, setSavingContractDefaults] = useState(false);
  const [tab, setTab] = useState<"documents" | "people">("documents");
  const [filter, setFilter] = useState("ALL");
  const [documentView, setDocumentView] = useState<"people" | "documents">("people");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [expandedPeople, setExpandedPeople] = useState<Set<string>>(() => new Set());
  const [selectedPeople, setSelectedPeople] = useState<Set<string>>(() => new Set());
  const [selectedDirectoryPeople, setSelectedDirectoryPeople] = useState<Set<string>>(() => new Set());
  const [missingDraftPreview, setMissingDraftPreview] = useState<DraftGenerationPreview | null>(null);
  const [missingDraftResult, setMissingDraftResult] = useState<MissingDraftGenerationResult | null>(null);
  const [batchGenerationPreview, setBatchGenerationPreview] = useState<DraftGenerationPreview | null>(null);
  const [batchGenerationResult, setBatchGenerationResult] = useState<DocumentBatchGenerationResult | null>(null);
  const [peopleImportResult, setPeopleImportResult] = useState<PeopleImportResult | null>(null);
  const [confirmBatchGenerate, setConfirmBatchGenerate] = useState(false);
  const [confirmMissingDrafts, setConfirmMissingDrafts] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [composer, setComposer] = useState<"person" | "document" | null>(null);
  const [editing, setEditing] = useState<ManagedDocument | null>(null);
  const [editingPerson, setEditingPerson] = useState<DocumentPerson | null>(null);
  const [editingEmployment, setEditingEmployment] = useState<{ person: DocumentPerson; assignment: EmploymentSummary } | null>(null);
  const [editOptionsPerson, setEditOptionsPerson] = useState<DocumentPerson | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<ManagedDocument | null>(null);
  const [signatureLink, setSignatureLink] = useState<(SignatureLink & { email_sent?: boolean; recipient?: string | null; delivery_error?: string | null }) | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewLoadingId, setPreviewLoadingId] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState("");
  const previewController = useRef<AbortController | null>(null);
  const [confirmCancel, setConfirmCancel] = useState<ManagedDocument | null>(null);
  const [confirmNewVersion, setConfirmNewVersion] = useState<ManagedDocument | null>(null);
  const [confirmSend, setConfirmSend] = useState<ManagedDocument | null>(null);
  const [confirmBundle, setConfirmBundle] = useState<{ contract: ManagedDocument; epp: ManagedDocument } | null>(null);
  const [bundleResult, setBundleResult] = useState<DocumentPairSendResult | null>(null);
  const [activeEmailBatchId, setActiveEmailBatchId] = useState<string | null>(null);
  const [emailBatch, setEmailBatch] = useState<DocumentEmailBatch | null>(null);
  const [emailBatchReady, setEmailBatchReady] = useState(false);
  const [retryingEmailBatch, setRetryingEmailBatch] = useState(false);
  const [confirmSelectedBundles, setConfirmSelectedBundles] = useState(false);
  const [paperPrintOpen, setPaperPrintOpen] = useState(false);
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [assignExistingOpen, setAssignExistingOpen] = useState(false);
  const [personForm, setPersonForm] = useState({ first_name: "", last_name: "", rut: "", email: "", phone: "", address: "", commune: "", position: "", area: "", workplace: "", start_date: "", end_date: "", remuneration: "" });
  const [employmentForm, setEmploymentForm] = useState({ position: "", duties: "", area: "", workplace: "", start_date: "", end_date: "", remuneration: "" });
  const [docForm, setDocForm] = useState({ person_id: "", kind: "CONTRACT" as "CONTRACT" | "EPP", event_id: "", title: "", contract_date: new Date().toISOString().slice(0, 10), employer_name: "", employer_rut: "", representative_name: "", representative_rut: "", employer_address: "", employer_commune: "Santiago", duties: "", workplace: "", riohs_received: false, eirl_completed: false, delivery_date: "", items: CATALOG });

  const clientQuery = isAdmin ? clientId : user?.client_id || "";
  const eventQuery = supervisor ? eventId : eventId;
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const params = qs({ client_id: clientQuery || undefined, event_id: eventQuery || undefined });
      const [personRows, documentRows, stats] = await Promise.all([
        documentApi.people(params), documentApi.documents(params), documentApi.summary(params),
      ]);
      setPeople(personRows); setDocuments(documentRows); setSummary(stats);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "No pudimos cargar Documentos.";
      setError(message);
    } finally { setLoading(false); }
  }, [clientQuery, eventQuery]);

  useEffect(() => {
    if (!user) return;
    if (isAdmin) void getClients({ limit: 100 }).then((result) => {
      setClients(result.items);
      if (!clientId && result.items.length === 1) setClientId(result.items[0].id);
    }).catch(() => setClients([]));
  }, [user, isAdmin, clientId]);

  useEffect(() => {
    if (!user) return;
    void documentApi.contractDefaults().then(setContractDefaults).catch((cause) => {
      setError(cause instanceof Error ? cause.message : "No se pudieron cargar los datos base del contrato.");
    });
  }, [user]);

  useEffect(() => {
    if (!user || !eventId || !isAdmin) {
      setEventContractDefaults(EMPTY_CONTRACT_DEFAULTS);
      return;
    }
    void documentApi.eventContractDefaults(eventId).then(setEventContractDefaults).catch((cause) => {
      toast({ title: "No se pudieron cargar los datos de contrato de la faena", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
      setEventContractDefaults(contractDefaults);
    });
  }, [user, eventId, isAdmin, contractDefaults, toast]);

  useEffect(() => {
    if (!user || !eventId) {
      setEventEppItems(CATALOG.map(({ item_code, label }) => ({ item_code, label })));
      return;
    }
    void documentApi.eventEppTemplate(eventId).then((template) => setEventEppItems(template.items))
      .catch((cause) => toast({ title: "No se pudo cargar la configuración EPP", description: cause instanceof Error ? cause.message : undefined, tone: "error" }));
  }, [user, eventId, toast]);

  useEffect(() => {
    if (!user) { setEvents([]); return; }
    void getEvents({ limit: 100, ...(clientQuery ? { client_id: clientQuery } : {}) })
      .then((result) => setEvents(result.items)).catch(() => setEvents([]));
  }, [user, supervisor, clientQuery, eventId]);

  useEffect(() => { if (user && (!supervisor || eventId)) void load(); }, [load, user, supervisor, eventId]);
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);
  useEffect(() => () => { previewController.current?.abort(); }, []);

  useEffect(() => {
    const storedBatchId = window.localStorage.getItem(DOCUMENT_EMAIL_BATCH_STORAGE_KEY);
    if (storedBatchId) { setActiveEmailBatchId(storedBatchId); setEmailBatchReady(true); }
  }, []);

  useEffect(() => {
    if (!user || !activeEmailBatchId || !emailBatchReady) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const batch = await documentApi.getTogetherBatch(activeEmailBatchId);
        if (disposed) return;
        setEmailBatch(batch);
        const finished = batch.status === "COMPLETED" || batch.status === "COMPLETED_WITH_ERRORS";
        if (!finished) timer = setTimeout(() => void poll(), 2000);
      } catch (cause) {
        if (disposed) return;
        if (cause instanceof ApiError && cause.status === 404) {
          window.localStorage.removeItem(DOCUMENT_EMAIL_BATCH_STORAGE_KEY);
          setActiveEmailBatchId(null);
          setEmailBatch(null);
          setEmailBatchReady(false);
          toast({ title: "El lote anterior no quedó guardado", description: "Ya puedes volver a seleccionar a las personas e iniciar el envío con la cola activa.", tone: "error" });
          return;
        }
        toast({ title: "No se pudo actualizar el avance del envío", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
        timer = setTimeout(() => void poll(), 5000);
      }
    };
    void poll();
    return () => { disposed = true; clearTimeout(timer); };
  }, [activeEmailBatchId, emailBatchReady, user, toast]);

  const visibleDocuments = useMemo(() => documents.filter((doc) => {
    if ((filter === "CONTRACT" || filter === "EPP") && doc.kind !== filter) return false;
    if (filter === "PENDING" && !["DRAFT", "READY", "SENT", "VIEWED", "PARTIALLY_SIGNED"].includes(doc.status)) return false;
    if (filter === "COMPLETED" && doc.status !== "COMPLETED") return false;
    if (filter === "PROBLEM" && !["CANCELLED", "EXPIRED", "SUPERSEDED"].includes(doc.status)) return false;
    if (filter === "MISSING") {
      const kinds = new Set(documents.filter((item) => item.person_id === doc.person_id && item.event_id === doc.event_id).map((item) => item.kind));
      if (kinds.size >= 2) return false;
    }
    const needle = search.trim().toLocaleLowerCase("es-CL");
    if (!needle) return true;
    const person = people.find((candidate) => candidate.id === doc.person_id);
    const eventName = events.find((event) => event.id === doc.event_id)?.name || "";
    return [doc.person_name, doc.person_rut, doc.title, person?.email || "", person?.phone || "", eventName]
      .some((value) => value.toLocaleLowerCase("es-CL").includes(needle));
  }), [documents, filter, search, people, events]);
  const searchedDocuments = visibleDocuments;
  const directoryPeople = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("es-CL");
    if (!needle) return people;
    return people.filter((person) => [person.first_name, person.last_name, person.rut, person.email || "", person.phone || ""]
      .some((value) => value.toLocaleLowerCase("es-CL").includes(needle)));
  }, [people, search]);
  const documentGroups = useMemo(() => {
    const grouped = new Map<string, ManagedDocument[]>();
    documents.filter((doc) => !eventId || doc.event_id === eventId).forEach((doc) => {
      const key = `${doc.person_id}:${doc.event_id || "global"}`;
      grouped.set(key, [...(grouped.get(key) || []), doc]);
    });
    if (eventId) people.forEach((person) => {
      const assignment = getEmploymentSummary(person);
      if (assignment?.event_id === eventId) {
        const key = `${person.id}:${eventId}`;
        if (!grouped.has(key)) grouped.set(key, []);
      }
    });
    const needle = search.trim().toLocaleLowerCase("es-CL");
    const groups = Array.from(grouped.entries()).map(([groupKey, docs]) => {
      const person = people.find((candidate) => candidate.id === docs[0]?.person_id) || people.find((candidate) => `${candidate.id}:${eventId || "global"}` === groupKey);
      const employment = person ? getEmploymentSummary(person) : null;
      const eventName = events.find((event) => event.id === (docs[0]?.event_id || employment?.event_id))?.name || "";
      const name = docs[0]?.person_name || (person ? `${person.first_name} ${person.last_name}` : "Persona");
      const rut = docs[0]?.person_rut || person?.rut || "";
      const groupDocuments = docs.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
      if ((filter === "CONTRACT" && !groupDocuments.some((doc) => doc.kind === "CONTRACT")) || (filter === "EPP" && !groupDocuments.some((doc) => doc.kind === "EPP"))) return null;
      if (filter === "PENDING" && groupDocuments.length && new Set(groupDocuments.map((doc) => doc.kind)).size >= 2 && !groupDocuments.some((doc) => ["DRAFT", "READY", "SENT", "VIEWED", "PARTIALLY_SIGNED"].includes(doc.status))) return null;
      if (filter === "COMPLETED" && !groupDocuments.some((doc) => doc.status === "COMPLETED")) return null;
      if (filter === "MISSING" && new Set(groupDocuments.map((doc) => doc.kind)).size >= 2) return null;
      if (filter === "PROBLEM" && !groupDocuments.some((doc) => ["CANCELLED", "EXPIRED", "SUPERSEDED"].includes(doc.status))) return null;
      if (positionFilter && employment?.position !== positionFilter) return null;
      if (needle && ![name, rut, person?.email || "", person?.phone || "", eventName, employment?.position || "", employment?.area || "", ...groupDocuments.map((doc) => doc.title)].some((value) => value.toLocaleLowerCase("es-CL").includes(needle))) return null;
      return {
      groupKey,
      personId: docs[0]?.person_id || person?.id || "",
      eventId: docs[0]?.event_id || employment?.event_id || null,
      docs: groupDocuments,
      name,
      rut,
      position: employment?.position || "",
      area: employment?.area || "",
      };
    }).filter((group): group is NonNullable<typeof group> => group !== null);
    return groups.sort((a, b) => a.name.localeCompare(b.name, "es-CL"));
  }, [documents, people, events, eventId, filter, positionFilter, search]);
  const pageSize = 25;
  const pageCount = Math.max(1, Math.ceil(documentGroups.length / pageSize));
  const pagedDocumentGroups = documentGroups.slice((page - 1) * pageSize, page * pageSize);
  const bundlePairs = useMemo(() => documents.filter((doc) => doc.kind === "CONTRACT" && doc.signature_method !== "PAPER" && ["DRAFT", "READY", "SENT", "VIEWED"].includes(doc.status)).flatMap((contract) => {
    const epp = documents.find((candidate) => candidate.kind === "EPP" && candidate.signature_method !== "PAPER" && candidate.person_id === contract.person_id && candidate.event_id === contract.event_id && candidate.employment_id === contract.employment_id && ["DRAFT", "READY", "SENT", "VIEWED"].includes(candidate.status));
    return epp ? [{ contract, epp }] : [];
  }), [documents]);
  const selectablePeople = useMemo(() => new Set((eventId && (filter === "ALL" || filter === "PENDING") ? pagedDocumentGroups : [])
    .filter((group) => bundlePairs.some((pair) => pair.contract.person_id === group.personId && pair.contract.event_id === group.eventId))
    .map((group) => group.groupKey)), [pagedDocumentGroups, bundlePairs, filter, eventId]);

  useEffect(() => { setPage(1); setSelectedPeople(new Set()); setSelectedDirectoryPeople(new Set()); }, [search, filter, positionFilter, eventId, clientId, tab, documentView]);
  useEffect(() => { if (page > pageCount) setPage(pageCount); }, [page, pageCount]);

  function resetPerson() {
    setEditingPerson(null);
    setEditingEmployment(null);
    setPersonForm({ first_name: "", last_name: "", rut: "", email: "", phone: "", address: "", commune: "", position: "", area: "", workplace: "", start_date: "", end_date: "", remuneration: "" });
    setComposer("person");
  }

  function openEditPerson(person: DocumentPerson) {
    setEditingPerson(person);
    setEditingEmployment(null);
    setPersonForm({ first_name: person.first_name, last_name: person.last_name, rut: person.rut, email: person.email || "", phone: person.phone || "", address: person.address || "", commune: person.commune || "", position: "", area: "", workplace: "", start_date: "", end_date: "", remuneration: "" });
    setComposer(null);
  }

  function openEditEmployment(person: DocumentPerson) {
    const assignment = getEmploymentSummary(person);
    if (!assignment) {
      toast({ title: "No hay una asignaciÃ³n para editar", description: "Selecciona la faena correspondiente y vuelve a abrir Personas.", tone: "error" });
      return;
    }
    setEditingPerson(null);
    setEditingEmployment({ person, assignment });
    setEmploymentForm({ position: assignment.position || "", duties: assignment.duties || "", area: assignment.area || "", workplace: assignment.workplace || "", start_date: assignment.start_date || "", end_date: assignment.end_date || "", remuneration: assignment.remuneration || "" });
    setComposer(null);
  }

  function resetDocument(personId = "", kind: "CONTRACT" | "EPP" = "CONTRACT") {
    setEditing(null);
    const defaults = eventId ? eventContractDefaults : contractDefaults;
    setDocForm({ person_id: personId, kind, event_id: eventId, title: kind === "CONTRACT" ? "Contrato por Obra o Faena" : "Registro de recepción EPP / RIOHS / EIRL", contract_date: new Date().toISOString().slice(0, 10), ...defaults, duties: "", workplace: "", riohs_received: false, eirl_completed: false, delivery_date: new Date().toISOString().slice(0, 10), items: eventEppItems.map((item) => ({ ...item, received_at: "", returned_at: "", received_conformity: false })) });
    setComposer("document");
  }

  async function saveEventDefaults(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!eventId) return;
    setSavingEventContractDefaults(true);
    try {
      const { has_event_override: _override, ...values } = eventContractDefaults;
      const saved = await documentApi.saveEventContractDefaults(eventId, values);
      setEventContractDefaults(saved);
      toast({ title: "Datos de contrato de la faena guardados", description: "Se usarán en los próximos documentos de esta faena; los documentos existentes no cambian.", tone: "success" });
    } catch (cause) {
      toast({ title: "No se pudieron guardar los datos de la faena", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setSavingEventContractDefaults(false); }
  }

  async function resetEventDefaults() {
    if (!eventId) return;
    setSavingEventContractDefaults(true);
    try {
      const saved = await documentApi.resetEventContractDefaults(eventId);
      setEventContractDefaults(saved);
      toast({ title: "La faena volverá a usar los datos generales de Greenway", tone: "success" });
    } catch (cause) {
      toast({ title: "No se pudo restablecer la configuración", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setSavingEventContractDefaults(false); }
  }

  async function applyEmployerDefaultsToDrafts() {
    if (!eventId) return;
    setApplyingEmployerDefaults(true);
    try {
      const result = await documentApi.applyEmployerDefaultsToDrafts(eventId);
      setConfirmApplyEmployerDefaults(false);
      await load();
      const missing = result.missing_defaults.length
        ? ` Faltan datos base: ${result.missing_defaults.join(", ")}.`
        : "";
      toast({
        title: result.documents_updated
          ? `Se actualizaron ${result.documents_updated} borrador(es)`
          : "No había borradores que actualizar",
        description: `Se completaron ${result.fields_filled} campo(s) vacíos de empleador en ${result.documents_checked} contrato(s) revisados.${missing}`,
        tone: "success",
      });
    } catch (cause) {
      toast({ title: "No se pudieron aplicar los datos base", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setApplyingEmployerDefaults(false); }
  }

  async function openPersonHistory(group: { personId: string; name: string; eventId: string | null }) {
    if (!group.eventId) return;
    setHistoryPerson({ id: group.personId, name: group.name, eventId: group.eventId });
    setHistoryEntries([]);
    setHistoryLoading(true);
    try { setHistoryEntries(await documentApi.personHistory(group.personId, group.eventId)); }
    catch (cause) { toast({ title: "No se pudo cargar el historial", description: cause instanceof Error ? cause.message : undefined, tone: "error" }); }
    finally { setHistoryLoading(false); }
  }

  async function saveReusableContractDefaults(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSavingContractDefaults(true);
    try {
      const saved = await documentApi.saveContractDefaults(contractDefaults);
      setContractDefaults(saved);
      toast({ title: "Datos base guardados", description: "Se precargarán en los próximos contratos de Greenway.", tone: "success" });
    } catch (cause) {
      toast({ title: "No se pudieron guardar los datos", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setSavingContractDefaults(false); }
  }

  function openEppTemplateEditor() {
    setEditingEppItems(eventEppItems.map((item) => ({ ...item })));
    setEppTemplateOpen(true);
  }

  async function saveEppTemplate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!eventId) return;
    setSavingEppTemplate(true);
    try {
      const saved = await documentApi.saveEventEppTemplate(eventId, editingEppItems);
      setEventEppItems(saved.items);
      setEppTemplateOpen(false);
      toast({ title: "Elementos EPP del evento actualizados", description: `${saved.draft_documents_updated || 0} borrador(es) existente(s) se actualizaron. Los documentos enviados o completados conservan su lista original.`, tone: "success" });
    } catch (cause) {
      toast({ title: "No se pudo guardar la lista EPP", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setSavingEppTemplate(false); }
  }

  async function savePerson(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true);
    try {
      if (supervisor && !personForm.position.trim()) throw new Error("Indica el cargo para asociar la persona al evento.");
      const employment = personForm.position.trim() ? {
        event_id: eventId || undefined, position: personForm.position, area: personForm.area || undefined,
        workplace: personForm.workplace || undefined, start_date: personForm.start_date || undefined, end_date: personForm.end_date || undefined,
        remuneration: personForm.remuneration || undefined,
      } : undefined;
      await documentApi.createPerson({ ...personForm, email: personForm.email || undefined, client_id: clientQuery || undefined, employment });
      toast({ title: "Asignación guardada", description: "La ficha histórica de Greenway se reutilizó y la persona quedó asociada a esta faena.", tone: "success" });
      setComposer(null); await load();
    } catch (cause) { toast({ title: "No se pudo guardar", description: cause instanceof Error ? cause.message : "Revisa los datos.", tone: "error" }); }
    finally { setBusy(false); }
  }

  async function savePersonProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingPerson) return;
    setBusy(true);
    try {
      const affectedDrafts = documents.filter((doc) => doc.person_id === editingPerson.id && doc.status === "DRAFT").length;
      const frozenDocuments = documents.filter((doc) => doc.person_id === editingPerson.id && !["DRAFT", "CANCELLED", "SUPERSEDED"].includes(doc.status)).length;
      await documentApi.updatePerson(editingPerson.id, {
        first_name: personForm.first_name,
        last_name: personForm.last_name,
        rut: personForm.rut,
        email: personForm.email || null,
        phone: personForm.phone || null,
        address: personForm.address || null,
        commune: personForm.commune || null,
      }, eventId || getEmploymentSummary(editingPerson)?.event_id || undefined);
      toast({ title: "Ficha actualizada", description: `${affectedDrafts} borrador(es) reflejarán los datos actuales al revisarlos. ${frozenDocuments} documento(s) preparados o enviados conservan su versión congelada.`, tone: "success" });
      setComposer(null);
      setEditingPerson(null);
      await load();
    } catch (cause) {
      toast({ title: "No se pudo actualizar la persona", description: cause instanceof Error ? cause.message : "Revisa los datos.", tone: "error" });
    } finally { setBusy(false); }
  }

  async function saveEmployment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingEmployment) return;
    setBusy(true);
    try {
      const { person, assignment } = editingEmployment;
      const draftsForAssignment = documents.filter((doc) => doc.person_id === person.id && doc.event_id === assignment.event_id && doc.employment_id === assignment.id && doc.status === "DRAFT").length;
      const frozenForAssignment = documents.filter((doc) => doc.person_id === person.id && doc.event_id === assignment.event_id && doc.employment_id === assignment.id && !["DRAFT", "CANCELLED", "SUPERSEDED"].includes(doc.status)).length;
      await documentApi.updateEmployment(person.id, assignment.id, {
        position: employmentForm.position,
        duties: employmentForm.duties || null,
        area: employmentForm.area || null,
        workplace: employmentForm.workplace || null,
        start_date: employmentForm.start_date || null,
        end_date: employmentForm.end_date || null,
        remuneration: employmentForm.remuneration || null,
      }, eventId || assignment.event_id || undefined);
      toast({ title: "Asignación actualizada", description: `${draftsForAssignment} borrador(es) mostrarán los datos corregidos al abrir la vista previa. ${frozenForAssignment} documento(s) preparados/enviados conservan su versión original.`, tone: "success" });
      setComposer(null);
      setEditingEmployment(null);
      await load();
    } catch (cause) {
      toast({ title: "No se pudo actualizar la asignaciÃ³n", description: cause instanceof Error ? cause.message : "Revisa los datos.", tone: "error" });
    } finally { setBusy(false); }
  }

  async function handleImportPreview() {
    if (!importFile) return;
    setBusy(true);
    try { setImportPreview(await documentApi.previewImport(importFile)); }
    catch (cause) { toast({ title: "No se pudo leer el Excel", description: cause instanceof Error ? cause.message : undefined, tone: "error" }); }
    finally { setBusy(false); }
  }

  async function commitImport() {
    if (!importPreview || importPreview.errors.length || !eventId) return;
    setBusy(true);
    try {
      const result = await documentApi.commitImport({ client_id: clientQuery || undefined, event_id: eventId, rows: importPreview.valid_rows });
      setPeopleImportResult(result);
      toast({ title: result.workers_failed ? "Importación completada con filas pendientes" : "Importación completada", description: `${result.created} personas nuevas · ${result.updated} actualizadas · ${result.assignments} asignaciones${result.workers_failed ? ` · ${result.workers_failed} fila(s) para reintentar` : ""}`, tone: result.workers_failed ? "error" : "success" });
      await load();
    } catch (cause) { toast({ title: "No se pudo importar", description: cause instanceof Error ? cause.message : undefined, tone: "error" }); }
    finally { setBusy(false); }
  }

  async function retryFailedPeopleImportRows() {
    if (!peopleImportResult || !importPreview) return;
    const failedRuts = new Set(peopleImportResult.results.filter((row) => row.status === "ERROR").map((row) => row.rut.replace(/[.\s]/g, "").toUpperCase()));
    const rows = importPreview.valid_rows.filter((row) => failedRuts.has(String(row.rut || "").replace(/[.\s]/g, "").toUpperCase()));
    if (!rows.length) return;
    setBusy(true);
    try {
      const retry = await documentApi.commitImport({ client_id: clientQuery || undefined, event_id: eventId, rows });
      setPeopleImportResult((previous) => {
        if (!previous) return retry;
        const merged = new Map(previous.results.map((row) => [row.rut.replace(/[.\s]/g, "").toUpperCase(), row]));
        retry.results.forEach((row) => merged.set(row.rut.replace(/[.\s]/g, "").toUpperCase(), row));
        const results = Array.from(merged.values());
        return {
          created: results.filter((row) => row.person_action === "created").length,
          updated: results.filter((row) => row.person_action === "updated").length,
          assignments: results.filter((row) => row.status === "SUCCESS").length,
          workers_processed: results.length,
          workers_failed: results.filter((row) => row.status === "ERROR").length,
          results,
        };
      });
      await load();
      toast({ title: "Reintento finalizado", description: `${retry.workers_failed} fila(s) siguen pendientes.`, tone: retry.workers_failed ? "error" : "success" });
    } catch (cause) {
      toast({ title: "No se pudo reintentar", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setBusy(false); }
  }

  async function generateMissingDrafts() {
    if (!eventId || selectedDirectoryPeople.size === 0) return;
    if (!missingDraftPreview) {
      await previewMissingDraftGeneration();
      setConfirmMissingDrafts(false);
      return;
    }
    setBusy(true);
    try {
      const result = await documentApi.generateMissingDrafts(eventId, Array.from(selectedDirectoryPeople));
      setMissingDraftResult(result);
      setMissingDraftPreview(null);
      setSelectedDirectoryPeople(new Set());
      await load();
      toast({
        title: "Revisión de documentos completada",
        description: `${result.documents_created} borrador(es) creado(s); ${result.documents_skipped} documento(s) existente(s) se conservaron.${result.setup_warnings.length ? ` Completa los datos base: ${result.setup_warnings.join(", ")}.` : ""}`,
        tone: "success",
      });
    } catch (cause) {
      toast({ title: "No se pudieron generar los borradores", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setBusy(false); }
  }

  async function previewMissingDraftGeneration() {
    if (!eventId || selectedDirectoryPeople.size === 0) return;
    await previewMissingDraftsFor(Array.from(selectedDirectoryPeople));
  }

  async function previewMissingDraftsFor(personIds: string[]) {
    if (!eventId || personIds.length === 0) return;
    setBusy(true);
    try { setMissingDraftPreview(await documentApi.previewMissingDrafts(eventId, personIds)); }
    catch (cause) { toast({ title: "No se pudo revisar la generación", description: cause instanceof Error ? cause.message : undefined, tone: "error" }); }
    finally { setBusy(false); }
  }

  function toggleDirectoryPerson(personId: string) {
    setSelectedDirectoryPeople((current) => {
      const next = new Set(current);
      if (next.has(personId)) next.delete(personId);
      else next.add(personId);
      return next;
    });
  }

  function toggleAllDirectoryPeople() {
    setSelectedDirectoryPeople((current) => current.size === directoryPeople.length
      && directoryPeople.every((person) => current.has(person.id))
      ? new Set()
      : new Set([...Array.from(current), ...directoryPeople.map((person) => person.id)]));
  }

  async function downloadEventDocumentSummary() {
    if (!eventId) return;
    try {
      const blob = await documentApi.eventDocumentStatus(eventId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      const eventFileName = (events.find((event) => event.id === eventId)?.name || "faena")
        .normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase();
      anchor.download = `estado-documentos-${eventFileName || "faena"}.xlsx`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (cause) {
      toast({ title: "No se pudo exportar el estado documental", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    }
  }

  async function previewBatchDrafts() {
    if (!importPreview || importPreview.errors.length || !eventId) return;
    setBusy(true);
    try {
      const preview = await documentApi.previewImportAndGenerate({
        client_id: clientQuery || undefined,
        event_id: eventId,
        rows: importPreview.valid_rows,
      });
      setBatchGenerationPreview(preview);
    } catch (cause) {
      toast({ title: "No se pudo preparar la revisión", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setBusy(false); }
  }

  async function generateBatchDrafts(rows = importPreview?.valid_rows || []) {
    if (rows.length === 0 || !eventId) return;
    if (!batchGenerationPreview && rows.length === importPreview?.valid_rows.length) {
      await previewBatchDrafts();
      setConfirmBatchGenerate(false);
      return;
    }
    setBusy(true);
    try {
      const result = await documentApi.importAndGenerate({ client_id: clientQuery || undefined, event_id: eventId, rows });
      setBatchGenerationPreview(null);
      setBatchGenerationResult(result);
      await load();
      setTab("documents");
      toast({
        title: result.workers_failed ? "Importación completada con filas pendientes" : "Borradores del lote generados",
        description: `${result.people_created} personas nuevas · ${result.people_updated} actualizadas · ${result.documents_created} documentos creados · ${result.documents_skipped} existentes preservados${result.workers_failed ? ` · ${result.workers_failed} fila(s) para reintentar` : ""}.`,
        tone: result.workers_failed ? "error" : "success",
      });
    } catch (cause) {
      toast({ title: "No se pudieron generar los documentos", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setBusy(false); }
  }

  async function retryFailedImportRows() {
    if (!batchGenerationResult || !importPreview) return;
    const failedRuts = new Set(batchGenerationResult.results.filter((row) => row.status === "ERROR").map((row) => row.rut.replace(/[.\s]/g, "").toUpperCase()));
    const rows = importPreview.valid_rows.filter((row) => failedRuts.has(String(row.rut || "").replace(/[.\s]/g, "").toUpperCase()));
    if (!rows.length) return;
    setBusy(true);
    try {
      const retry = await documentApi.importAndGenerate({ client_id: clientQuery || undefined, event_id: eventId, rows });
      setBatchGenerationResult((previous) => {
        if (!previous) return retry;
        const merged = new Map(previous.results.map((row) => [row.rut.replace(/[.\s]/g, "").toUpperCase(), row]));
        retry.results.forEach((row) => merged.set(row.rut.replace(/[.\s]/g, "").toUpperCase(), row));
        const results = Array.from(merged.values());
        return {
          ...retry,
          workers_processed: results.length,
          people_created: results.filter((row) => row.person_action === "created").length,
          people_updated: results.filter((row) => row.person_action === "updated").length,
          assignments_created: results.filter((row) => row.assignment_action === "created").length,
          contracts_created: results.filter((row) => row.created.includes("CONTRACT")).length,
          epp_documents_created: results.filter((row) => row.created.includes("EPP")).length,
          documents_created: results.reduce((total, row) => total + row.created.length, 0),
          documents_skipped: results.reduce((total, row) => total + row.already_had.length, 0),
          workers_failed: results.filter((row) => row.status === "ERROR").length,
          results,
        };
      });
      await load();
      toast({ title: "Reintento finalizado", description: `${retry.workers_failed} fila(s) siguen pendientes.`, tone: retry.workers_failed ? "error" : "success" });
    } catch (cause) {
      toast({ title: "No se pudo reintentar", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setBusy(false); }
  }

  async function saveDocument(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true);
    try {
      const data = { contract_date: docForm.contract_date, employer_name: docForm.employer_name,
        employer_rut: docForm.employer_rut, representative_name: docForm.representative_name,
        representative_rut: docForm.representative_rut, employer_address: docForm.employer_address,
        employer_commune: docForm.employer_commune, duties: docForm.duties, workplace: docForm.workplace };
      const epp = docForm.kind === "EPP" ? { riohs_received: docForm.riohs_received,
        eirl_completed: docForm.eirl_completed, delivery_date: docForm.delivery_date || undefined,
        items: docForm.items.map((item) => ({ ...item, received_at: item.received_at || undefined, returned_at: item.returned_at || undefined })) } : undefined;
      if (editing) await documentApi.updateDocument(editing.id, { title: docForm.title, data, epp });
      else await documentApi.createDocument({ person_id: docForm.person_id, kind: docForm.kind,
        event_id: docForm.event_id || undefined, title: docForm.title, data, epp });
      toast({ title: editing ? "Borrador actualizado" : "Borrador creado", tone: "success" });
      setComposer(null); setEditing(null); await load();
    } catch (cause) { toast({ title: "No se pudo guardar el documento", description: cause instanceof Error ? cause.message : undefined, tone: "error" }); }
    finally { setBusy(false); }
  }

  async function editDocument(doc: ManagedDocument) {
    setEditing(doc);
    const data = doc.data || {};
    setDocForm({ person_id: doc.person_id, kind: doc.kind, event_id: doc.event_id || "", title: doc.title,
      contract_date: String(data.contract_date || "").slice(0, 10), employer_name: String(data.employer_name || ""),
      employer_rut: String(data.employer_rut || ""), representative_name: String(data.representative_name || ""),
      representative_rut: String(data.representative_rut || ""), employer_address: String(data.employer_address || ""),
      employer_commune: String(data.employer_commune || "Santiago"), duties: String(data.duties || ""), workplace: String(data.workplace || ""),
      riohs_received: Boolean(doc.epp?.riohs_received), eirl_completed: Boolean(doc.epp?.eirl_completed),
      delivery_date: doc.epp?.delivery_date || "", items: (doc.epp?.items || []).map((item) => ({ ...item, received_at: item.received_at || "", returned_at: item.returned_at || "" })) });
    setComposer("document");
  }

  async function createNewVersion(doc: ManagedDocument) {
    setBusy(true);
    try {
      const version = await documentApi.newVersion(doc.id);
      setFilter("PENDING");
      await load();
      toast({
        title: `Versión ${version.version} creada como borrador`,
        description: "La versión anterior quedó en el historial y su enlace fue revocado. Revisa y edita el borrador antes de enviarlo al trabajador.",
        tone: "success",
      });
    } catch (cause) {
      toast({ title: "No se pudo crear versión", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function openPreview(doc: ManagedDocument) {
    if (previewController.current) return;
    const controller = new AbortController();
    previewController.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 60_000);
    setSelectedDocument(doc);
    setPreviewError("");
    setPreviewUrl("");
    setPreviewLoadingId(doc.id);
    try {
      const blob = await documentApi.previewPdf(doc.id, controller.signal);
      if (previewController.current === controller) setPreviewUrl(URL.createObjectURL(blob));
    } catch (cause) {
      if (!controller.signal.aborted) setPreviewError(cause instanceof Error ? cause.message : "No se pudo generar la vista previa.");
      else if (previewController.current === controller) setPreviewError("La vista previa tardó demasiado. Puedes volver a intentarlo.");
    } finally {
      window.clearTimeout(timeout);
      if (previewController.current === controller) {
        previewController.current = null;
        setPreviewLoadingId(null);
      }
    }
  }

  function closePreview() {
    previewController.current?.abort();
    previewController.current = null;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl("");
    setPreviewError("");
    setPreviewLoadingId(null);
    setSelectedDocument(null);
  }

  async function prepareDocument(doc: ManagedDocument, confirmAfterPrepare = false) {
    setBusy(true);
    try {
      const prepared = await documentApi.prepare(doc.id);
      setSelectedDocument(prepared);
      if (confirmAfterPrepare) setConfirmSend(prepared);
      toast({ title: "Documento preparado", description: "Ya puedes generar el enlace de firma.", tone: "success" });
      await load();
    } catch (cause) {
      toast({ title: "No se pudo preparar el documento", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setBusy(false); }
  }

  async function performSend() {
    if (!confirmSend) return;
    const doc = confirmSend;
    setBusy(true);
    try { const result = await documentApi.send(doc.id); setSignatureLink({ ...result.link, email_sent: result.email_sent, recipient: result.recipient, delivery_error: result.delivery_error }); setSelectedDocument(result.document); setConfirmSend(null); await load(); }
    catch (cause) { toast({ title: "No se pudo preparar el enlace", description: cause instanceof Error ? cause.message : undefined, tone: "error" }); }
    finally { setBusy(false); }
  }

  async function performSendBundle() {
    if (!confirmBundle) return;
    setBusy(true);
    try {
      const result = await documentApi.sendTogether(confirmBundle.contract.id, confirmBundle.epp.id);
      setConfirmBundle(null); setBundleResult(result);
      toast({ title: result.email_sent ? "Correo enviado" : "Enlaces preparados", description: result.email_sent ? `Se enviaron ambos documentos a ${result.recipient}.` : result.delivery_error || "En local no se envían correos reales; comparte los enlaces de prueba.", tone: result.delivery_error ? "error" : "success" });
      await load();
    } catch (cause) { toast({ title: "No se pudieron enviar juntos", description: cause instanceof Error ? cause.message : undefined, tone: "error" }); }
    finally { setBusy(false); }
  }

  async function performSendSelectedBundles() {
    const pairs = bundlePairs.filter(({ contract }) => selectedPeople.has(`${contract.person_id}:${contract.event_id || "global"}`));
    if (!pairs.length || !eventId) return;
    const batchId = crypto.randomUUID();
    setBusy(true);
    setConfirmSelectedBundles(false);
    setActiveEmailBatchId(batchId);
    setEmailBatch(null);
    setEmailBatchReady(false);
    window.localStorage.setItem(DOCUMENT_EMAIL_BATCH_STORAGE_KEY, batchId);
    try {
      const batch = await documentApi.enqueueTogetherBatch({
        batch_id: batchId,
        event_id: eventId,
        pairs: pairs.map(({ contract, epp }) => ({ contract_document_id: contract.id, epp_document_id: epp.id })),
      });
      setEmailBatch(batch);
      setEmailBatchReady(true);
      setSelectedPeople(new Set());
      toast({ title: "Lote guardado", description: "El servidor continuará procesando los correos aunque cierres esta página.", tone: "success" });
      await load();
    } catch (cause) {
      // Keep the batch id: the server may have accepted it even if the response was interrupted.
      setEmailBatchReady(true);
      toast({ title: "No se pudo confirmar el lote", description: cause instanceof Error ? cause.message : "Se comprobará si el servidor alcanzó a guardarlo.", tone: "error" });
      try { setEmailBatch(await documentApi.getTogetherBatch(batchId)); } catch { /* Polling retries while the saved id exists. */ }
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function retryFailedEmailBatch() {
    if (!emailBatch || !activeEmailBatchId || emailBatch.failed === 0) return;
    setRetryingEmailBatch(true);
    try {
      const failedIds = emailBatch.items.filter((item) => item.status === "FAILED").map((item) => item.id);
      const batch = await documentApi.retryTogetherBatch(activeEmailBatchId, failedIds);
      setEmailBatch(batch);
      toast({ title: "Reintento en cola", description: `${failedIds.length} envío(s) volverán a procesarse en segundo plano.`, tone: "success" });
    } catch (cause) {
      toast({ title: "No se pudo reintentar el lote", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setRetryingEmailBatch(false); }
  }

  function dismissEmailBatch() {
    if (emailBatch && !["COMPLETED", "COMPLETED_WITH_ERRORS"].includes(emailBatch.status)) return;
    window.localStorage.removeItem(DOCUMENT_EMAIL_BATCH_STORAGE_KEY);
    setActiveEmailBatchId(null);
    setEmailBatch(null);
    setEmailBatchReady(false);
  }

  function togglePersonSelection(groupKey: string) {
    setSelectedPeople((current) => {
      const next = new Set(current);
      if (next.has(groupKey)) next.delete(groupKey);
      else next.add(groupKey);
      return next;
    });
  }

  function toggleAllVisiblePeople() {
    setSelectedPeople((current) => {
      const next = new Set(current);
      const allSelected = Array.from(selectablePeople).every((groupKey) => next.has(groupKey));
      selectablePeople.forEach((groupKey) => allSelected ? next.delete(groupKey) : next.add(groupKey));
      return next;
    });
  }

  function togglePersonExpanded(groupKey: string) {
    setExpandedPeople((current) => {
      const next = new Set(current);
      if (next.has(groupKey)) next.delete(groupKey);
      else next.add(groupKey);
      return next;
    });
  }

  function renderDocumentActions(doc: ManagedDocument) {
    if (doc.signature_method === "PAPER") return <div className="space-y-2"><PaperDocumentActions document={doc} onDone={() => void load()}/><div className="flex flex-wrap gap-1.5"><Button size="sm" variant="secondary" disabled={Boolean(previewLoadingId)} onClick={() => void openPreview(doc)}>{previewLoadingId === doc.id ? <><LoaderCircle className="h-4 w-4 animate-spin"/>Generando vista…</> : "Ver PDF"}</Button>{doc.has_original_pdf && <Button size="sm" variant="ghost" title="Descargar PDF para papel" onClick={() => void download(doc)}><Download className="h-4 w-4"/></Button>}{["DRAFT", "READY", "CANCELLED"].includes(doc.status) && <Button size="sm" variant="ghost" disabled={busy} onClick={() => setConfirmNewVersion(doc)}>Nueva versión</Button>}</div></div>;
    const paperEligible = isAdmin && Boolean(doc.event_id) && ["DRAFT", "READY"].includes(doc.status) && doc.signature_method !== "ELECTRONIC";
    return <div className="flex flex-wrap gap-1.5">
      {paperEligible && <PaperDocumentActions document={doc} allowPrepare onDone={() => void load()}/>}
      <Button size="sm" variant="secondary" disabled={Boolean(previewLoadingId)} onClick={() => void openPreview(doc)}>{previewLoadingId === doc.id ? <><LoaderCircle className="h-4 w-4 animate-spin"/>Generando vista…</> : "Ver"}</Button>
      {doc.can_edit && <Button size="sm" variant="secondary" onClick={() => void editDocument(doc)}>Editar</Button>}
      {doc.can_edit && <Button size="sm" onClick={() => void sendDocument(doc)}>Enviar</Button>}
      {["SENT", "VIEWED"].includes(doc.status) && <Button size="sm" variant="secondary" onClick={() => void sendDocument(doc)}>Reenviar</Button>}
      {doc.has_original_pdf && <Button size="sm" variant="ghost" title="Descargar PDF original" onClick={() => void download(doc)}><Download className="h-4 w-4"/></Button>}
      {doc.has_signed_pdf && <Button size="sm" variant="secondary" onClick={() => void download(doc, true)}>Firmado</Button>}
      {doc.status === "COMPLETED" && <Button size="sm" variant="secondary" disabled={busy} onClick={() => void resendSignedCopy(doc)}>Reenviar copia</Button>}
      {doc.status === "PARTIALLY_SIGNED" && <Button size="sm" onClick={() => void supervisorSign(doc)}>Completar firma</Button>}
      {["SENT", "VIEWED", "PARTIALLY_SIGNED", "COMPLETED", "EXPIRED"].includes(doc.status) && <Button size="sm" variant="ghost" disabled={busy} onClick={() => setConfirmNewVersion(doc)}>Nueva versión</Button>}
      {!["COMPLETED", "CANCELLED", "SUPERSEDED", "EXPIRED"].includes(doc.status) && <Button size="sm" variant="ghost" onClick={() => setConfirmCancel(doc)}>Cancelar</Button>}
    </div>;
  }

  function renderGroupedDocuments() {
    const selectedBundles = bundlePairs.filter(({ contract }) => selectedPeople.has(`${contract.person_id}:${contract.event_id || "global"}`));
    const allVisibleSelected = selectablePeople.size > 0 && Array.from(selectablePeople).every((groupKey) => selectedPeople.has(groupKey));
    const missingPeopleIds = pagedDocumentGroups.filter((group) => group.eventId && new Set(group.docs.map((doc) => doc.kind)).size < 2).map((group) => group.personId);
    return <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div><p className="font-semibold text-slate-900">Personal de la faena</p><p className="text-sm text-slate-500">{documentGroups.length} personas · {searchedDocuments.length} documentos visibles</p></div>
        <div className="flex flex-wrap items-center gap-3">{isAdmin && eventId && <Button size="sm" variant="secondary" onClick={() => setPaperPrintOpen(true)}><Printer className="h-4 w-4"/> Imprimir lote</Button>}{missingPeopleIds.length > 0 && <><Button size="sm" variant="secondary" onClick={() => setSelectedDirectoryPeople(new Set([...Array.from(selectedDirectoryPeople), ...missingPeopleIds]))}>Seleccionar faltantes ({missingPeopleIds.length})</Button><Button size="sm" disabled={busy} onClick={() => { setSelectedDirectoryPeople(new Set(missingPeopleIds)); void previewMissingDraftsFor(missingPeopleIds); }}>Revisar creación faltante</Button></>}{!eventId && <p className="text-sm text-slate-500">Selecciona una faena arriba para habilitar el envío masivo.</p>}{selectablePeople.size > 0 && <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-600"><input aria-label="Seleccionar todos los envíos conjuntos disponibles de esta página" checked={allVisibleSelected} className="h-4 w-4 accent-emerald-700" onChange={toggleAllVisiblePeople} type="checkbox"/>Seleccionar disponibles</label>}</div>
      </div>
      {loading ? <div className="rounded-xl border bg-white p-12 text-center text-slate-500"><LoaderCircle className="mx-auto h-6 w-6 animate-spin"/><p className="mt-2">Cargando documentos…</p></div>
        : documentGroups.length === 0 ? <div className="rounded-xl border bg-white p-5"><EmptyState icon={<FileText className="h-6 w-6"/>} title={search ? "No encontramos coincidencias" : "Aún no hay documentos"} description={search ? "Prueba con otro nombre, RUT o título de documento." : "Crea una persona y prepara su contrato o registro EPP para esta faena."} action={!search ? <Button onClick={() => resetDocument(people[0]?.id || "")}>Crear documento</Button> : undefined}/></div>
        : <div className="space-y-2">{pagedDocumentGroups.map((group) => {
          const person = people.find((candidate) => candidate.id === group.personId);
          const latestOfKind = (kind: ManagedDocument["kind"]) => group.docs.filter((doc) => doc.kind === kind).sort((a, b) => b.version - a.version || b.updated_at.localeCompare(a.updated_at))[0];
          const contract = latestOfKind("CONTRACT");
          const epp = latestOfKind("EPP");
          const personBundles = bundlePairs.filter((pair) => pair.contract.person_id === group.personId && pair.contract.event_id === group.eventId);
          const expanded = expandedPeople.has(group.groupKey);
          return <article className={"overflow-hidden rounded-xl border bg-white shadow-sm transition " + (selectedPeople.has(group.groupKey) ? "border-emerald-400 ring-1 ring-emerald-200" : "border-slate-200")} key={group.groupKey}>
            <div className="grid gap-3 p-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(260px,1fr)_auto] lg:items-center">
              <div className="flex min-w-0 items-center gap-3">
                {selectablePeople.has(group.groupKey) && <input aria-label={"Seleccionar envío conjunto de " + group.name} checked={selectedPeople.has(group.groupKey)} className="h-4 w-4 shrink-0 accent-emerald-700" onChange={() => togglePersonSelection(group.groupKey)} type="checkbox"/>}
                <button aria-expanded={expanded} aria-label={(expanded ? "Ocultar" : "Ver") + " documentos de " + group.name} className="rounded-md p-1 text-slate-500 hover:bg-slate-100" onClick={() => togglePersonExpanded(group.groupKey)} type="button">{expanded ? <ChevronDown className="h-4 w-4"/> : <ChevronRight className="h-4 w-4"/>}</button>
                <div className="min-w-0"><p className="truncate font-semibold text-slate-900">{group.name}</p><p className="truncate text-xs text-slate-500">{group.rut}{person?.email ? " · " + person.email : ""}{group.eventId ? ` · ${events.find((event) => event.id === group.eventId)?.name || "Faena"}` : " · Global"}</p></div>
              </div>
              <div className="flex flex-wrap gap-2">{(["CONTRACT", "EPP"] as const).map((kind) => {
                const doc = kind === "CONTRACT" ? contract : epp;
                const label = kind === "CONTRACT" ? "Contrato" : "EPP";
                const paperLabel: Record<string, string> = { PREPARED: "Papel · preparado", PRINTED: "Papel · impreso", SIGNED_RECEIVED: "Papel · firmado", ARCHIVED: "Papel · archivado" };
                return <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs" key={kind}><span className="font-medium text-slate-600">{label}</span>{doc ? <span className={"rounded-full px-2 py-0.5 font-semibold " + (doc.signature_method === "PAPER" ? paperStatusClasses[doc.paper_status || "PREPARED"] : doc.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" : ["CANCELLED", "EXPIRED", "SUPERSEDED"].includes(doc.status) ? "bg-rose-100 text-rose-800" : "bg-amber-100 text-amber-800")}>{doc.signature_method === "PAPER" ? paperLabel[doc.paper_status || "PREPARED"] : statuses[doc.status] || doc.status}</span> : <span className="rounded-full bg-amber-100 px-2 py-0.5 font-semibold text-amber-800">Faltante</span>}</span>;
              })}</div>
              <div className="flex items-center justify-between gap-3 lg:justify-end"><span className="whitespace-nowrap text-xs text-slate-500">{group.docs.length} doc.</span><Button size="sm" variant="secondary" onClick={() => void openPersonHistory(group)}>Historial</Button><Button size="sm" variant="secondary" onClick={() => { setTab("people"); setSearch(""); }}>Personas</Button></div>
            </div>
            {expanded && <div className="border-t border-slate-100 bg-slate-50/70 p-4">
              {personBundles.map(({ contract: pairedContract, epp: pairedEpp }) => <div className="mb-2 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50/70 px-3 py-2" key={pairedContract.id + ":" + pairedEpp.id}><div><p className="text-sm font-semibold text-slate-800">Contrato + EPP listos para envío conjunto</p><p className="text-xs text-slate-500">{pairedContract.title} · {pairedEpp.title}</p></div><Button size="sm" disabled={busy} onClick={() => setConfirmBundle({ contract: pairedContract, epp: pairedEpp })}>Enviar ambos juntos</Button></div>)}
              <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-white text-[11px] uppercase tracking-wide text-slate-500"><tr>{["Documento", "Faena", "Estado", "Actualizado", "Acciones"].map((heading) => <th className="px-3 py-2" key={heading}>{heading}</th>)}</tr></thead><tbody>{group.docs.map((doc) => { const paperLabels: Record<string, string> = { PREPARED: "Papel · preparado", PRINTED: "Papel · impreso", SIGNED_RECEIVED: "Papel · firmado recibido", ARCHIVED: "Papel · copia archivada" }; return <tr className="border-t border-slate-100" key={doc.id}><td className="px-3 py-3"><p className="font-medium text-slate-900">{doc.title}</p><p className="text-xs text-slate-500">{doc.kind === "CONTRACT" ? "Contrato por obra o faena" : "EPP / RIOHS / EIRL"} · v{doc.version}{doc.signature_method === "PAPER" ? " · Firma en papel" : doc.signature_method === "ELECTRONIC" ? " · Firma electrónica" : ""}</p></td><td className="px-3 py-3 text-xs text-slate-600">{doc.event_id ? events.find((event) => event.id === doc.event_id)?.name || "Evento asociado" : "Global"}</td><td className="px-3 py-3"><span className={"rounded-full px-2.5 py-1 text-xs font-semibold " + (doc.signature_method === "PAPER" ? paperStatusClasses[doc.paper_status || "PREPARED"] : doc.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" : ["CANCELLED", "EXPIRED", "SUPERSEDED"].includes(doc.status) ? "bg-slate-100 text-slate-600" : "bg-amber-100 text-amber-800")}>{doc.signature_method === "PAPER" ? paperLabels[doc.paper_status || "PREPARED"] : statuses[doc.status] || doc.status}</span></td><td className="whitespace-nowrap px-3 py-3 text-xs text-slate-500">{new Date(doc.updated_at).toLocaleDateString("es-CL")}</td><td className="px-3 py-3">{renderDocumentActions(doc)}</td></tr>; })}</tbody></table></div>
            </div>}
          </article>;
        })}</div>}
      {documentGroups.length > 0 && <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500"><span>Mostrando {Math.min((page - 1) * pageSize + 1, documentGroups.length)}–{Math.min(page * pageSize, documentGroups.length)} de {documentGroups.length} personas</span><div className="flex items-center gap-2"><Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}><ChevronLeft className="h-4 w-4"/> Anterior</Button><span className="px-1 font-medium text-slate-700">{page} / {pageCount}</span><Button size="sm" variant="secondary" disabled={page >= pageCount} onClick={() => setPage((value) => Math.min(pageCount, value + 1))}>Siguiente <ChevronRight className="h-4 w-4"/></Button></div></div>}
      {selectedPeople.size > 0 && <div className="sticky bottom-3 z-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-300 bg-white/95 p-3 shadow-lg backdrop-blur"><div><p className="text-sm font-semibold text-slate-900">{selectedPeople.size} persona(s) seleccionada(s)</p><p className="text-xs text-slate-500">{selectedBundles.length} conjunto(s) disponible(s); cada trabajador recibirá un correo con un único enlace.</p></div><div className="flex gap-2"><Button variant="secondary" onClick={() => setSelectedPeople(new Set())}>Limpiar selección</Button><Button disabled={busy || selectedBundles.length === 0 || !eventId} onClick={() => setConfirmSelectedBundles(true)}>{busy ? "Guardando lote…" : "Enviar conjuntos seleccionados"}</Button></div></div>}
    </section>;
  }

  function sendDocument(doc: ManagedDocument) {
    if (doc.status === "DRAFT") {
      void prepareDocument(doc, true);
      return;
    }
    setConfirmSend(doc);
  }

  async function download(doc: ManagedDocument, signed = false) {
    try { const blob = await documentApi.download(doc.id, signed); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `document-${doc.id}-${signed ? "signed" : "original"}.pdf`; anchor.click(); URL.revokeObjectURL(url); }
    catch (cause) { toast({ title: "No se pudo descargar el PDF", description: cause instanceof Error ? cause.message : undefined, tone: "error" }); }
  }

  async function performCancel() {
    if (!confirmCancel) return;
    try { await documentApi.cancel(confirmCancel.id); toast({ title: "Documento cancelado", tone: "success" }); setConfirmCancel(null); await load(); }
    catch (cause) { toast({ title: "No se pudo cancelar", description: cause instanceof Error ? cause.message : undefined, tone: "error" }); }
  }

  async function supervisorSign(doc: ManagedDocument) {
    try { await documentApi.supervisorSign(doc.id); toast({ title: "Documento completado", description: "Se generó el PDF final con las firmas manuscritas registradas.", tone: "success" }); await load(); }
    catch (cause) { toast({ title: "No se pudo completar", description: cause instanceof Error ? cause.message : undefined, tone: "error" }); }
  }

  async function resendSignedCopy(doc: ManagedDocument) {
    setBusy(true);
    try {
      const result = await documentApi.resendSignedCopy(doc.id);
      toast({ title: result.email_sent ? "Copia firmada reenviada" : "No se envió el correo", description: result.email_sent ? `Se envió a ${result.recipient}.` : "El envío de correo está deshabilitado fuera de producción.", tone: result.email_sent ? "success" : "error" });
    } catch (cause) {
      toast({ title: "No se pudo reenviar la copia firmada", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setBusy(false); }
  }

  async function copyLink() {
    if (!signatureLink) return;
    await navigator.clipboard.writeText(signatureLink.url);
    toast({ title: "Enlace copiado", description: "Compártelo con el trabajador por un canal privado.", tone: "success" });
  }

  return <RoleGuard roles={["SUPER_ADMIN", "ADMIN", ...(supervisor ? ["SUPERVISOR" as const] : [])]}>
    <div className="space-y-6" data-documents-view={tab === "documents" ? documentView : "directory"}>
      <PageHeader eyebrow="Gestión documental" title="Documentos" description="Legajo histórico de personas de Greenway y documentos independientes por cada faena." actions={<Button disabled={!eventId} onClick={resetPerson}><Plus className="h-4 w-4"/> Asignar persona a faena</Button>} />
      {emailBatch && <section aria-live="polite" className="space-y-3 rounded-xl border border-emerald-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-semibold text-slate-900">Envío masivo {emailBatch.status === "COMPLETED" || emailBatch.status === "COMPLETED_WITH_ERRORS" ? "finalizado" : "en proceso"}</h2><p className="text-sm text-slate-600">El servidor seguirá trabajando aunque cierres el navegador. Al volver, este avance se recupera automáticamente.</p></div><div className="flex gap-2">{emailBatch.failed > 0 && <Button size="sm" disabled={retryingEmailBatch} onClick={() => void retryFailedEmailBatch()}>{retryingEmailBatch ? "Encolando…" : `Reintentar ${emailBatch.failed} fallido(s)`}</Button>}{["COMPLETED", "COMPLETED_WITH_ERRORS"].includes(emailBatch.status) && <Button size="sm" variant="secondary" onClick={dismissEmailBatch}>Quitar seguimiento</Button>}</div></div>
        {(() => { const processed = emailBatch.sent + emailBatch.prepared + emailBatch.failed; const percentage = emailBatch.total ? Math.min(100, Math.round(processed / emailBatch.total * 100)) : 100; return <><div className="h-2.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-600 transition-all" style={{ width: `${percentage}%` }}/></div><div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-600"><span>{processed} de {emailBatch.total} procesados ({percentage}%)</span><span>{emailBatch.sent} correos enviados</span><span>{emailBatch.prepared} enlaces preparados</span><span>{emailBatch.processing} procesando</span><span>{emailBatch.queued} en cola</span>{emailBatch.failed > 0 && <span className="font-semibold text-rose-700">{emailBatch.failed} con error</span>}{emailBatch.skipped > 0 && <span>{emailBatch.skipped} omitidos</span>}</div></>; })()}
        <div className="max-h-64 space-y-2 overflow-auto">{emailBatch.items.map((item) => <article className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2 text-sm" key={item.id}><div><span className="font-medium text-slate-800">{item.person_name}</span><span className="ml-2 text-xs text-slate-500">{item.email || "Sin correo"}</span>{item.error && <p className="text-xs text-rose-700">{item.error}</p>}</div><span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.status === "FAILED" ? "bg-rose-100 text-rose-800" : ["SENT", "PREPARED"].includes(item.status) ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{({ QUEUED: "En cola", PROCESSING: "Preparando", SENDING: "Enviando", RETRYING: "Reintentando", SENT: "Correo enviado", PREPARED: "Enlace preparado", FAILED: "Error" } as Record<string, string>)[item.status]}</span>{item.result?.links.map((link) => <a className="text-xs font-medium text-emerald-800 underline" href={link.url} key={link.url} rel="noreferrer" target="_blank">Abrir enlace</a>)}</article>)}</div>
      </section>}
      {isAdmin && <details className="rounded-xl border border-emerald-200 bg-white p-4 shadow-sm"><summary className="cursor-pointer font-semibold text-slate-900">Datos base de Greenway para contratos</summary><p className="mt-2 text-sm text-slate-600">Guarda una vez los datos del empleador y representante. Se precargarán al crear los próximos contratos.</p><form className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" onSubmit={(event) => void saveReusableContractDefaults(event)}>{([ ["employer_name", "Razón social empleador"], ["employer_rut", "RUT empleador"], ["representative_name", "Representante legal"], ["representative_rut", "RUT representante"], ["employer_address", "Domicilio empresa"], ["employer_commune", "Comuna empresa"] ] as Array<[keyof DocumentContractDefaults, string]>).map(([key, label]) => <label className={fieldClass} key={key}>{label}<Input value={String(contractDefaults[key] || "")} onChange={(event) => setContractDefaults((old) => ({ ...old, [key]: event.target.value }))}/></label>)}<div className="flex items-end justify-end sm:col-span-2 lg:col-span-3"><Button disabled={savingContractDefaults}>{savingContractDefaults ? "Guardando..." : "Guardar datos reutilizables"}</Button></div></form></details>}
      {isAdmin && <RepresentativeSignatureSettings representativeName={contractDefaults.representative_name} representativeRut={contractDefaults.representative_rut} toast={toast}/>}
      {isAdmin && eventId && <details className="rounded-xl border border-sky-200 bg-white p-4 shadow-sm"><summary className="cursor-pointer font-semibold text-slate-900">Datos de contrato para esta faena</summary><p className="mt-2 text-sm text-slate-600">Puedes personalizar aquí los datos del empleador/representante para esta faena. Si no guardas una excepción, se usarán los datos generales de Greenway.</p><p className="mt-1 text-xs font-medium text-sky-800">{eventContractDefaults.has_event_override ? "Esta faena tiene valores propios." : "Actualmente usa los valores generales."}</p><form className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" onSubmit={(event) => void saveEventDefaults(event)}>{([ ["employer_name", "Razón social empleador"], ["employer_rut", "RUT empleador"], ["representative_name", "Representante legal"], ["representative_rut", "RUT representante"], ["employer_address", "Domicilio empresa"], ["employer_commune", "Comuna empresa"] ] as Array<[keyof DocumentContractDefaults, string]>).map(([key, label]) => <label className={fieldClass} key={key}>{label}<Input value={String(eventContractDefaults[key] || "")} onChange={(event) => setEventContractDefaults((old) => ({ ...old, [key]: event.target.value }))}/></label>)}<div className="flex flex-wrap items-end justify-end gap-2 sm:col-span-2 lg:col-span-3"><Button type="button" variant="secondary" disabled={savingEventContractDefaults || !eventContractDefaults.has_event_override} onClick={() => void resetEventDefaults()}>Usar datos generales</Button><Button disabled={savingEventContractDefaults}>{savingEventContractDefaults ? "Guardando…" : "Guardar para esta faena"}</Button><Button type="button" variant="secondary" disabled={applyingEmployerDefaults} onClick={() => setConfirmApplyEmployerDefaults(true)}>{applyingEmployerDefaults ? "Actualizando borradores…" : "Aplicar a borradores existentes"}</Button></div></form><p className="mt-2 text-xs text-slate-500">La acción solo rellena datos del empleador que estén vacíos en contratos en borrador de esta faena; no sobrescribe campos ya completados ni modifica documentos enviados o completados.</p></details>}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
        {[["Personas", summary.people, Users], ["Documentos", summary.documents, FileText], ["Pendientes", summary.pending, FilePlus2], ["Completados", summary.completed, FileCheck2], ["EPP / seguridad", summary.incomplete_epp, ShieldCheck]].map(([label, value, Icon]) => {
          const Glyph = Icon as typeof FileText;
          return <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3 shadow-sm" key={String(label)}><span className="text-xs font-medium text-slate-500">{label as string}</span><div className="flex items-center gap-2"><Glyph className="h-4 w-4 text-emerald-700"/><span className="text-xl font-bold text-slate-900">{value as number}</span></div></div>;
        })}
      </div>
      {(isAdmin || supervisor) && <div className="flex flex-wrap items-end gap-3 rounded-xl border bg-white p-4">
        {isAdmin && <label className={fieldClass}>Cliente<select className="h-10 min-w-64 rounded-md border bg-white px-3" value={clientId} onChange={(e) => { setClientId(e.target.value); setEventId(""); }}><option value="">Todos los clientes</option>{clients.map((client) => <option key={client.id} value={client.id}>{client.business_name}</option>)}</select></label>}
        <label className={fieldClass}>Faena / evento<select className="h-10 min-w-64 rounded-md border bg-white px-3" value={eventId} onChange={(e) => setEventId(e.target.value)}><option value="">Selecciona una faena</option>{events.map((event) => <option key={event.id} value={event.id}>{event.name}</option>)}</select></label>
        {isAdmin && <p className="text-xs text-slate-500">Cada asignación y documento debe pertenecer a una faena concreta.</p>}
      </div>}
      {isAdmin && eventId && tab === "documents" && <section className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-emerald-200 bg-emerald-50/60 p-4">
        <div><h2 className="font-semibold text-slate-900">Elementos EPP de {events.find((event) => event.id === eventId)?.name || "esta faena"}</h2><p className="mt-1 text-sm text-slate-600">{eventEppItems.length ? eventEppItems.map((item) => item.label).join(" · ") : "No hay elementos configurados"}</p><p className="mt-1 text-xs text-slate-500">Se aplica a documentos nuevos y borradores de esta faena. Enviados o completados mantienen su lista.</p></div>
        <Button variant="secondary" onClick={openEppTemplateEditor}><Pencil className="h-4 w-4"/> Configurar elementos</Button>
      </section>}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200">
        {tab === "people" && <label className="relative my-2 min-w-[260px] flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"/><Input aria-label="Buscar personas por nombre o RUT" className="pl-9" onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por nombre, RUT o contacto…" value={search}/></label>}
        {tab === "documents" && <div className="flex w-full flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <label className="relative min-w-[260px] flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"/><Input aria-label="Buscar documentos o personas" className="pl-9" onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por nombre, RUT o documento…" value={search}/></label>
          <div aria-label="Modo de visualización" className="flex rounded-lg bg-slate-100 p-1">
            <button aria-pressed={documentView === "people"} className={"rounded-md px-3 py-2 text-sm font-semibold " + (documentView === "people" ? "bg-white text-emerald-800 shadow-sm" : "text-slate-600")} onClick={() => setDocumentView("people")} type="button">Por persona</button>
            <button aria-pressed={documentView === "documents"} className={"rounded-md px-3 py-2 text-sm font-semibold " + (documentView === "documents" ? "bg-white text-emerald-800 shadow-sm" : "text-slate-600")} onClick={() => setDocumentView("documents")} type="button">Todos los documentos</button>
          </div>
        </div>}
        <div className="flex gap-2"><button className={`border-b-2 px-3 py-3 text-sm font-semibold ${tab === "documents" ? "border-emerald-700 text-emerald-800" : "border-transparent text-slate-500"}`} onClick={() => setTab("documents")}>Documentos</button><button className={`border-b-2 px-3 py-3 text-sm font-semibold ${tab === "people" ? "border-emerald-700 text-emerald-800" : "border-transparent text-slate-500"}`} onClick={() => setTab("people")}>Personas</button></div>
        {tab === "documents" ? <div className="flex flex-wrap items-center gap-2 pb-1">{[["ALL", "Todos"], ["CONTRACT", "Contratos"], ["EPP", "EPP / Seguridad"], ["PENDING", "Pendientes"], ["COMPLETED", "Completados"], ["MISSING", "Faltantes"], ["PROBLEM", "Con problema"]].map(([key, label]) => <button className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-semibold ${filter === key ? "bg-emerald-800 text-white" : "text-slate-600 hover:bg-slate-100"}`} key={key} onClick={() => setFilter(key)}>{label}</button>)}{eventId && documentView === "people" && <select aria-label="Filtrar por cargo" className="h-9 rounded-md border bg-white px-3 text-xs" value={positionFilter} onChange={(event) => setPositionFilter(event.target.value)}><option value="">Todos los cargos</option>{Array.from(new Set(people.map((person) => getEmploymentSummary(person)?.position).filter((position): position is string => Boolean(position)))).sort((a, b) => a.localeCompare(b, "es-CL")).map((position) => <option key={position} value={position}>{position}</option>)}</select>}</div> : <div className="flex flex-wrap gap-2 pb-2"><label className="flex h-9 cursor-pointer items-center gap-2 rounded-md border bg-white px-3 text-sm font-semibold"><Upload className="h-4 w-4"/> Importar Excel<input accept=".xlsx" className="sr-only" type="file" onChange={(e) => { setImportFile(e.target.files?.[0] || null); setImportPreview(null); }}/></label><Button size="sm" variant="secondary" onClick={async () => { const blob = await documentApi.template(); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "greenway-personas.xlsx"; a.click(); URL.revokeObjectURL(url); }}>Descargar plantilla</Button>{importFile && <Button size="sm" disabled={busy} onClick={() => void handleImportPreview()}>{busy ? "Analizando…" : "Analizar archivo"}</Button>}{isAdmin && <Button size="sm" variant="secondary" onClick={() => setAssignExistingOpen(true)}><Users className="h-4 w-4"/> Reutilizar de otra faena</Button>}</div>}
      </div>
      {importPreview && <section className="rounded-xl border border-slate-200 bg-white p-4" aria-live="polite"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold">Vista previa de importación</h2><p className="text-sm text-slate-500">{importPreview.total_rows} filas · {importPreview.valid_count} listas · {importPreview.error_count} con errores</p>{eventId && <p className="mt-1 text-xs text-emerald-800">Faena seleccionada: {events.find((event) => event.id === eventId)?.name || "evento actual"}</p>}</div><div className="flex flex-wrap gap-2"><Button variant="secondary" disabled={busy || !eventId || importPreview.errors.length > 0 || importPreview.valid_count === 0} onClick={() => void commitImport()}>{busy ? "Importando…" : "Solo importar personal"}</Button><Button disabled={busy || !eventId || importPreview.errors.length > 0 || importPreview.valid_count === 0} onClick={() => setConfirmBatchGenerate(true)}>{busy ? "Preparando…" : `Importar + generar ${importPreview.valid_count * 2} borradores`}</Button></div></div><p className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-900">La planilla se asociará a la faena seleccionada. Por trabajador se crearán un contrato y un registro EPP, usando sus datos y los datos base de Greenway. Se guardarán como borradores; no se enviará ningún correo.</p>{importPreview.errors.length > 0 && <div className="mt-3 max-h-44 overflow-auto rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{importPreview.errors.map((item, index) => <p key={`${item.row}-${index}`}>Fila {item.row} · {item.field}: {item.message}</p>)}<p className="mt-2 font-semibold">Corrige el Excel y vuelve a analizar; no se importará parcialmente.</p></div>}{importPreview.valid_rows.length > 0 && <div className="mt-3 overflow-auto"><table className="w-full text-left text-xs"><thead><tr>{["RUT", "NOMBRE", "APELLIDO", "CARGO", "LABORES / FUNCIONES", "FAENA", "EMAIL"].map((header) => <th className="p-2" key={header}>{header}</th>)}</tr></thead><tbody>{importPreview.valid_rows.slice(0, 10).map((row, index) => <tr className="border-t" key={index}>{["rut", "first_name", "last_name", "position", "duties", "workplace", "email"].map((key) => <td className="p-2" key={key}>{String(row[key] || "—")}</td>)}</tr>)}</tbody></table>{importPreview.valid_rows.length > 10 && <p className="mt-2 text-xs text-slate-500">Mostrando las primeras 10 filas.</p>}</div>}</section>}
      {tab === "documents" && documentView === "documents" && bundlePairs.length > 0 && <section className="space-y-3 rounded-xl border border-emerald-200 bg-emerald-50/50 p-4"><div><h2 className="font-semibold text-slate-900">Envío conjunto al trabajador</h2><p className="text-sm text-slate-600">Envía en un solo correo el contrato y el registro EPP de la misma persona y faena.</p></div><div className="grid gap-2 md:grid-cols-2">{bundlePairs.map(({ contract, epp }) => <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white p-3" key={`${contract.id}:${epp.id}`}><div><p className="font-medium">{contract.person_name}</p><p className="text-xs text-slate-500">{contract.title} + {epp.title}</p></div><Button size="sm" onClick={() => setConfirmBundle({ contract, epp })}>Enviar ambos juntos</Button></div>)}</div></section>}
      {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {tab === "documents" && documentView === "people" && renderGroupedDocuments()}
      {tab === "documents" ? <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">{loading ? <div className="p-12 text-center text-slate-500"><LoaderCircle className="mx-auto h-6 w-6 animate-spin"/><p className="mt-2">Cargando documentos…</p></div> : visibleDocuments.length === 0 ? <div className="p-5"><EmptyState icon={<FileText className="h-6 w-6"/>} title="Aún no hay documentos" description="Crea una persona y prepara su contrato o registro EPP. Los documentos pueden ser globales o asociados a un evento." action={<Button onClick={() => resetDocument(people[0]?.id || "")}>Crear documento</Button>}/></div> : <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr>{["Persona", "Documento", "Contexto", "Estado", "Actualizado", "Acciones"].map((heading) => <th className="px-4 py-3" key={heading}>{heading}</th>)}</tr></thead><tbody>{visibleDocuments.map((doc) => <tr className="border-t border-slate-100" key={doc.id}><td className="px-4 py-3"><p className="font-semibold text-slate-900">{doc.person_name}</p><p className="text-xs text-slate-500">{doc.person_rut}</p></td><td className="px-4 py-3"><p className="font-medium">{doc.title}</p><p className="text-xs text-slate-500">{doc.kind === "CONTRACT" ? "Contrato por obra o faena" : "EPP / RIOHS / EIRL"} · v{doc.version}</p></td><td className="px-4 py-3 text-slate-600">{doc.event_id ? events.find((event) => event.id === doc.event_id)?.name || "Evento asociado" : "Global"}</td><td className="px-4 py-3"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${doc.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" : doc.status === "CANCELLED" || doc.status === "EXPIRED" ? "bg-slate-100 text-slate-600" : "bg-amber-100 text-amber-800"}`}>{statuses[doc.status] || doc.status}</span></td><td className="px-4 py-3 text-xs text-slate-500">{new Date(doc.updated_at).toLocaleDateString("es-CL")}</td><td className="px-4 py-3"><div className="flex flex-wrap gap-1.5"><Button size="sm" variant="secondary" onClick={() => void openPreview(doc)}>Ver</Button>{doc.can_edit && <Button size="sm" variant="secondary" onClick={() => void editDocument(doc)}>Editar</Button>}{doc.can_edit && <Button size="sm" onClick={() => void sendDocument(doc)}>Enviar</Button>}{["SENT", "VIEWED"].includes(doc.status) && <Button size="sm" variant="secondary" onClick={() => void sendDocument(doc)}>Reenviar</Button>}{doc.has_original_pdf && <Button size="sm" variant="ghost" title="Descargar PDF original" onClick={() => void download(doc)}><Download className="h-4 w-4"/></Button>}{doc.has_signed_pdf && <Button size="sm" variant="secondary" onClick={() => void download(doc, true)}>Firmado</Button>}{doc.status === "COMPLETED" && <Button size="sm" variant="secondary" disabled={busy} onClick={() => void resendSignedCopy(doc)}>Reenviar copia</Button>}{doc.status === "PARTIALLY_SIGNED" && <Button size="sm" onClick={() => void supervisorSign(doc)}>Completar firma</Button>}{["SENT", "VIEWED", "PARTIALLY_SIGNED", "COMPLETED", "EXPIRED"].includes(doc.status) && <Button size="sm" variant="ghost" disabled={busy} onClick={() => setConfirmNewVersion(doc)}>Nueva versión</Button>}{!["COMPLETED", "CANCELLED", "SUPERSEDED", "EXPIRED"].includes(doc.status) && <Button size="sm" variant="ghost" onClick={() => setConfirmCancel(doc)}>Cancelar</Button>}</div></td></tr>)}</tbody></table></div>}</div> : <div className="space-y-3">{eventId && <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50/70 p-4"><div><p className="font-semibold text-emerald-950">Crear borradores pendientes de esta faena</p><p className="text-sm text-emerald-900">Selecciona personas; solo se crearán contrato o EPP si todavía no existen. Los documentos existentes y sus versiones se conservan.</p><p className="mt-1 text-xs text-emerald-800">{directoryPeople.length} trabajador(es) en esta vista · {selectedDirectoryPeople.size} seleccionado(s)</p></div><div className="flex flex-wrap gap-2"><Button size="sm" variant="secondary" disabled={!directoryPeople.length} onClick={toggleAllDirectoryPeople}>{selectedDirectoryPeople.size === directoryPeople.length && directoryPeople.length ? "Quitar selección" : `Seleccionar todos (${directoryPeople.length})`}</Button><Button size="sm" variant="secondary" onClick={downloadEventDocumentSummary}><Download className="h-4 w-4"/> Exportar estado</Button><Button size="sm" disabled={busy || selectedDirectoryPeople.size === 0} onClick={() => setConfirmMissingDrafts(true)}>{busy ? "Generando…" : `Crear borradores faltantes (${selectedDirectoryPeople.size})`}</Button></div></div>}{loading ? <div className="rounded-xl border bg-white p-10 text-center text-slate-500">Cargando personas…</div> : directoryPeople.length === 0 ? <div className="rounded-xl border bg-white p-5"><EmptyState icon={<Users className="h-6 w-6"/>} title={search ? "No encontramos personas" : "Aún no hay personas"} description={search ? "Prueba con otro nombre o RUT." : "Crea una ficha o importa varias personas desde una planilla Excel."} action={!search ? <Button onClick={resetPerson}>Crear persona</Button> : undefined}/></div> : <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm"><table className="w-full min-w-[820px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{eventId && <th className="w-12 px-4 py-3"><input aria-label="Seleccionar todas las personas de la faena" type="checkbox" checked={directoryPeople.length > 0 && directoryPeople.every((person) => selectedDirectoryPeople.has(person.id))} onChange={toggleAllDirectoryPeople}/></th>}{["Persona", "RUT", "Contacto", "Cargo / área", "Documentos"].map((heading) => <th className="px-4 py-3" key={heading}>{heading}</th>)}</tr></thead><tbody>{directoryPeople.map((person) => { const personDocs = documents.filter((doc) => doc.person_id === person.id && (!eventId || doc.event_id === eventId)); const assignment = getEmploymentSummary(person); return <tr className="border-t" key={person.id}>{eventId && <td className="px-4 py-3"><input aria-label={`Seleccionar a ${person.first_name} ${person.last_name}`} type="checkbox" checked={selectedDirectoryPeople.has(person.id)} onChange={() => toggleDirectoryPerson(person.id)}/></td>}<td className="px-4 py-3 font-semibold">{person.first_name} {person.last_name}</td><td className="px-4 py-3">{person.rut}</td><td className="px-4 py-3 text-slate-600">{person.email || person.phone || "—"}</td><td className="px-4 py-3 text-slate-600">{assignment?.position || "—"} · {assignment?.area || "Sin área"}</td><td className="px-4 py-3"><div className="flex items-center justify-end gap-2"><span className="whitespace-nowrap text-slate-600">{personDocs.length} doc.</span><Button size="sm" onClick={() => resetDocument(person.id)}>Nuevo documento</Button><Button size="sm" variant="ghost" title="Editar datos de persona o faena" aria-label={`Editar datos de ${person.first_name} ${person.last_name}`} onClick={() => setEditOptionsPerson(person)}><Pencil className="h-4 w-4"/></Button></div></td></tr>; })}</tbody></table></div>}</div>}
      {(composer === "person" || composer === "document") && <ModalShell size="lg" title={composer === "person" ? "Ficha de persona" : editing ? "Editar borrador" : "Preparar documento"} description={composer === "person" ? "Datos personales separados de la asignación laboral; no se crea una cuenta EcoEvent." : "Completa los datos estructurados. La vista previa se genera al solicitarla y el PDF se congela al enviar."} onClose={() => { setComposer(null); setEditing(null); }}>
        {composer === "person" ? <form className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => void savePerson(e)}>
          {[ ["first_name", "Nombre", true], ["last_name", "Apellido", true], ["rut", "RUT", true], ["email", "Correo", false], ["phone", "Teléfono", false], ["address", "Domicilio", false], ["commune", "Comuna", false], ["position", "Cargo / funciones", true], ["area", "Área", false], ["workplace", "Lugar de trabajo / dependencias", false], ["start_date", "Fecha de inicio", false], ["end_date", "Fecha de término", false], ["remuneration", "Remuneración diaria", false] ].map(([key, label, required]) => <label className={fieldClass} key={key as string}>{label as string}<Input required={Boolean(required)} type={key === "start_date" || key === "end_date" ? "date" : key === "email" ? "email" : key === "remuneration" ? "number" : "text"} value={personForm[key as keyof typeof personForm]} onChange={(e) => setPersonForm((old) => ({ ...old, [key as string]: e.target.value }))}/></label>)}
          <div className="flex justify-end gap-2 sm:col-span-2"><Button type="button" variant="secondary" onClick={() => setComposer(null)}>Cerrar</Button><Button disabled={busy}>{busy ? "Guardando…" : "Guardar persona"}</Button></div>
        </form> : <form className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => void saveDocument(e)}>
          {!editing && <label className={`${fieldClass} sm:col-span-2`}>Persona<select required className="h-10 rounded-md border px-3" value={docForm.person_id} onChange={(e) => setDocForm((old) => ({ ...old, person_id: e.target.value }))}><option value="">Selecciona una persona</option>{people.map((person) => <option key={person.id} value={person.id}>{person.first_name} {person.last_name} · {person.rut}</option>)}</select></label>}
          {!editing && <label className={fieldClass}>Tipo<select className="h-10 rounded-md border px-3" value={docForm.kind} onChange={(e) => resetDocument(docForm.person_id, e.target.value as "CONTRACT" | "EPP")}><option value="CONTRACT">Contrato por obra o faena</option><option value="EPP">Registro EPP / RIOHS / EIRL</option></select></label>}
          <label className={fieldClass}>Título<Input required value={docForm.title} onChange={(e) => setDocForm((old) => ({ ...old, title: e.target.value }))}/></label>
          <label className={fieldClass}>Faena / evento<select required disabled={Boolean(editing)} className="h-10 rounded-md border px-3" value={docForm.event_id} onChange={(e) => setDocForm((old) => ({ ...old, event_id: e.target.value }))}><option value="">Selecciona una faena</option>{events.map((event) => <option key={event.id} value={event.id}>{event.name}</option>)}</select></label>
          {docForm.kind === "CONTRACT" ? <>
            {[["contract_date", "Fecha de contrato", "date"], ["employer_name", "Razón social empleador", "text"], ["employer_rut", "RUT empleador", "text"], ["representative_name", "Representante legal", "text"], ["representative_rut", "RUT representante", "text"], ["employer_address", "Domicilio empresa", "text"], ["employer_commune", "Comuna empresa", "text"], ["duties", "Labores / funciones (opcional)", "text"], ["workplace", "Lugar / dependencias de trabajo (opcional)", "text"]].map(([key, label, type]) => <label className={fieldClass} key={key}>{label}<Input type={type} value={docForm[key as keyof typeof docForm] as string} onChange={(e) => setDocForm((old) => ({ ...old, [key]: e.target.value }))}/></label>)}
          </> : <>
            <p className="rounded-lg bg-sky-50 p-3 text-sm text-sky-900 sm:col-span-2">El trabajador completará esta constancia: marcará RIOHS/EIRL y los elementos que efectivamente reciba.</p>
            <div className="sm:col-span-2"><h3 className="mb-2 font-semibold">Elementos que aparecerán en la constancia</h3><div className="grid gap-2 sm:grid-cols-2">{docForm.items.map((item) => <p className="rounded-lg border bg-slate-50 p-3 text-sm" key={item.item_code}>{item.label}</p>)}</div></div>
          </>}
          <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900 sm:col-span-2">El flujo de firma de esta versión es local y simulado; no ofrece firma electrónica con validez legal. El texto contractual requiere revisión laboral antes de uso real.</p>
          <div className="flex justify-end gap-2 sm:col-span-2"><Button type="button" variant="secondary" onClick={() => { setComposer(null); setEditing(null); }}>Cerrar</Button><Button disabled={busy}>{busy ? "Guardando…" : editing ? "Guardar cambios" : "Crear borrador"}</Button></div>
        </form>}
      </ModalShell>}
      {eppTemplateOpen && <ModalShell size="lg" title="Configurar elementos de protección" description={`Esta lista se aplicará a los nuevos documentos y borradores EPP de ${events.find((event) => event.id === eventId)?.name || "la faena"}. Los enviados y completados no se modificarán.`} onClose={() => setEppTemplateOpen(false)}>
        <form className="space-y-4" onSubmit={(event) => void saveEppTemplate(event)}>
          <div className="space-y-2">{editingEppItems.map((item, index) => <div className="grid grid-cols-[1fr_auto] gap-2" key={item.item_code}><Input aria-label={`Elemento EPP ${index + 1}`} maxLength={100} required value={item.label} onChange={(event) => setEditingEppItems((items) => items.map((current, currentIndex) => currentIndex === index ? { ...current, label: event.target.value } : current))}/><Button aria-label={`Quitar ${item.label}`} type="button" variant="secondary" onClick={() => setEditingEppItems((items) => items.filter((_, currentIndex) => currentIndex !== index))}>Quitar</Button></div>)}</div>
          <Button type="button" variant="secondary" onClick={() => setEditingEppItems((items) => [...items, { item_code: `CUSTOM_${Date.now()}`, label: "" }])}><Plus className="h-4 w-4"/> Agregar elemento</Button>
          <div className="flex justify-end gap-2 border-t pt-4"><Button type="button" variant="secondary" onClick={() => setEppTemplateOpen(false)}>Cancelar</Button><Button disabled={savingEppTemplate || editingEppItems.length === 0}>{savingEppTemplate ? "Guardando…" : "Guardar lista del evento"}</Button></div>
        </form>
      </ModalShell>}
      {signatureLink && <ModalShell title={signatureLink.email_sent ? "Enlace enviado por correo" : "Enlace de firma preparado"} description={signatureLink.email_sent ? `Se envió el acceso al correo ${signatureLink.recipient}.` : "El acceso quedó generado; puedes copiarlo o compartir el QR de forma privada."} onClose={() => setSignatureLink(null)}><div className="grid gap-5 sm:grid-cols-[1fr_auto]"><div><p className="text-sm text-slate-600">Vence: {new Date(signatureLink.expires_at).toLocaleString("es-CL")}</p><div className="mt-3 break-all rounded-lg bg-slate-50 p-3 text-sm">{signatureLink.url}</div><Button className="mt-3" onClick={() => void copyLink()}><Clipboard className="h-4 w-4"/> Copiar enlace</Button></div><Image alt="Código QR para abrir el portal de firma" className="h-40 w-40 rounded-lg border p-2" height={160} src={signatureLink.qr_data_url} unoptimized width={160}/></div>{signatureLink.delivery_error && <p role="alert" className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{signatureLink.delivery_error}</p>}<p className="mt-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">{signatureLink.signature_notice}</p></ModalShell>}
      {selectedDocument && (previewUrl || previewLoadingId === selectedDocument.id || previewError) && <ModalShell size="lg" title={selectedDocument.title} description={selectedDocument.status === "PARTIALLY_SIGNED" ? "Vista previa con la firma manuscrita del trabajador. Completa el cierre administrativo para guardar el PDF final." : selectedDocument.status === "COMPLETED" ? "PDF final del documento con las firmas registradas." : "Vista previa temporal; no se guarda un PDF hasta enviar a firma."} onClose={closePreview}>
        {previewLoadingId === selectedDocument.id && <div className="flex h-[50vh] flex-col items-center justify-center gap-3 rounded-lg border border-slate-200 bg-slate-50 text-center"><LoaderCircle className="h-9 w-9 animate-spin text-emerald-700"/><p className="font-semibold text-slate-800">Preparando vista previa…</p><p className="text-sm text-slate-500">Puede tardar unos segundos. Mantén esta ventana abierta; no vuelvas a pulsar el botón.</p></div>}
        {previewError && <div className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-lg border border-rose-200 bg-rose-50 p-6 text-center"><p className="font-semibold text-rose-900">No se pudo abrir la vista previa</p><p className="text-sm text-rose-800">{previewError}</p><div className="flex gap-2"><Button variant="secondary" onClick={closePreview}>Cerrar</Button><Button onClick={() => void openPreview(selectedDocument)}>Intentar de nuevo</Button></div></div>}
        {previewUrl && <><iframe className="h-[70vh] w-full rounded-lg border" title={`Vista previa de ${selectedDocument.title}`} src={previewUrl}/>{["DRAFT", "READY"].includes(selectedDocument.status) && <div className="mt-4 flex justify-end gap-2">{selectedDocument.status === "DRAFT" ? <Button disabled={busy} onClick={() => void prepareDocument(selectedDocument)}>{busy ? "Preparando…" : "Preparar documento"}</Button> : <Button onClick={() => setConfirmSend(selectedDocument)}>Enviar a firma</Button>}</div>}</>}
      </ModalShell>}
      {confirmCancel && <ConfirmDialog open title="Cancelar documento" description="Se revocará el enlace de firma activo. El documento no se elimina y sus archivos existentes se conservan." confirmLabel="Cancelar documento" onClose={() => setConfirmCancel(null)} onConfirm={() => void performCancel()}/>}
      {confirmApplyEmployerDefaults && <ConfirmDialog open loading={applyingEmployerDefaults} title="Completar datos del empleador en borradores" description={`Se revisarán los contratos en borrador de ${events.find((event) => event.id === eventId)?.name || "esta faena"}. Solo se rellenarán los campos del empleador que estén vacíos con los datos base vigentes; no se sobrescribirán datos existentes ni se modificarán documentos enviados o completados.`} confirmLabel="Aplicar datos a borradores" onClose={() => setConfirmApplyEmployerDefaults(false)} onConfirm={() => void applyEmployerDefaultsToDrafts()}/>}
      {confirmNewVersion && <ConfirmDialog open loading={busy} title="Crear nueva versión" description={`Se conservará la versión ${confirmNewVersion.version} en el historial y se revocará su enlace activo. Se creará la versión ${confirmNewVersion.version + 1} como borrador para que puedas revisarla antes de enviarla.`} confirmLabel="Crear borrador de nueva versión" onClose={() => setConfirmNewVersion(null)} onConfirm={() => { const doc = confirmNewVersion; setConfirmNewVersion(null); void createNewVersion(doc); }}/>}
      {confirmBatchGenerate && importPreview && <ConfirmDialog open loading={busy} title="Generar documentos del evento" description={`Se importarán ${importPreview.valid_count} trabajadores para ${events.find((event) => event.id === eventId)?.name || "la faena seleccionada"} y se crearán hasta ${importPreview.valid_count * 2} borradores: un contrato y un registro EPP por trabajador. Si ya existe un documento para esa persona y evento, se conservará para evitar duplicados. No se enviará ningún correo.`} confirmLabel="Importar y generar borradores" onClose={() => setConfirmBatchGenerate(false)} onConfirm={() => void generateBatchDrafts()}/>}
      {confirmSend && <ConfirmDialog open loading={busy} title={confirmSend.can_edit ? "Enviar documento a firma" : "Reenviar enlace"} description={confirmSend.can_edit ? "Al confirmar, se aplicará la firma reutilizable del representante, se congelarán los datos y se guardará el PDF original de esta versión. El trabajador revisará el PDF, dibujará su firma y confirmará." : "El enlace activo se revocará y se creará uno nuevo para la misma versión del documento."} confirmLabel={confirmSend.can_edit ? "Autorizar firma y enviar" : "Revocar y reenviar"} onClose={() => setConfirmSend(null)} onConfirm={() => void performSend()}/>}
      {confirmBundle && <ConfirmDialog open loading={busy} title="Enviar contrato y EPP juntos" description={`Al confirmar, se aplicará la firma guardada del representante a ambos PDFs y se enviará un único correo con un solo acceso para que ${confirmBundle.contract.person_name} revise y firme cada documento. Si ya tenían enlaces activos, estos se reemplazarán.`} confirmLabel="Autorizar y enviar ambos" onClose={() => setConfirmBundle(null)} onConfirm={() => void performSendBundle()}/>}
      {bundleResult && <ModalShell size="lg" title={bundleResult.email_sent ? "Documentos enviados" : "Acceso conjunto preparado"} description={bundleResult.email_sent ? `Se envió un correo a ${bundleResult.recipient} con un solo acceso para ambos documentos.` : "En modo local no se envían correos reales. Abre este único acceso para probar los dos documentos."} onClose={() => setBundleResult(null)}><div className="space-y-4">{bundleResult.links.map((link) => <div className="grid gap-4 rounded-xl border p-4 sm:grid-cols-[1fr_auto]" key={link.url}><div><p className="font-semibold">Portal de documentos · Contrato + Registro EPP</p><a className="mt-2 block break-all text-sm text-emerald-800 underline" href={link.url} rel="noreferrer" target="_blank">Abrir el acceso único ↗</a><p className="mt-2 text-xs text-slate-500">Valida tu RUT una sola vez · Vence: {new Date(link.expires_at).toLocaleString("es-CL")}</p></div><Image alt="Código QR del portal único de documentos" className="h-32 w-32 rounded-lg border p-2" height={128} src={link.qr_data_url} unoptimized width={128}/></div>)}{bundleResult.delivery_error && <p role="alert" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{bundleResult.delivery_error}</p>}<p className="text-xs text-slate-500">El trabajador podrá cambiar entre los dos documentos en el portal y completar cada uno independientemente. La firma de esta versión es simulada y no tiene validez legal.</p></div></ModalShell>}
      {confirmMissingDrafts && <ConfirmDialog open loading={busy} title="Crear borradores que faltan" description={`Se revisarán ${selectedDirectoryPeople.size} personas de ${events.find((event) => event.id === eventId)?.name || "la faena seleccionada"}. Solo se crearán los tipos de documento faltantes; los existentes, enviados o completados no se duplicarán ni modificarán. No se enviarán correos.`} confirmLabel="Revisar y crear faltantes" onClose={() => setConfirmMissingDrafts(false)} onConfirm={() => void generateMissingDrafts()}/>}
      {missingDraftResult && <ModalShell size="lg" title="Resultado de generación de borradores" description={`${missingDraftResult.event_name} · ${missingDraftResult.documents_created} documento(s) creado(s) · ${missingDraftResult.documents_skipped} existente(s) conservado(s)`} onClose={() => setMissingDraftResult(null)}><div className="space-y-3"><div className="grid gap-2 sm:grid-cols-3"><div className="rounded-lg bg-emerald-50 p-3"><p className="text-xs text-emerald-800">Contratos creados</p><p className="text-xl font-bold text-emerald-950">{missingDraftResult.contracts_created}</p></div><div className="rounded-lg bg-sky-50 p-3"><p className="text-xs text-sky-800">Registros EPP creados</p><p className="text-xl font-bold text-sky-950">{missingDraftResult.epp_documents_created}</p></div><div className="rounded-lg bg-slate-100 p-3"><p className="text-xs text-slate-600">Existentes preservados</p><p className="text-xl font-bold text-slate-900">{missingDraftResult.documents_skipped}</p></div></div>{missingDraftResult.setup_warnings.length > 0 && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Completa los datos base de Greenway para que los contratos queden listos para revisión: {missingDraftResult.setup_warnings.join(", ")}.</p>}<div className="max-h-[50vh] overflow-y-auto rounded-lg border"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-3 py-2">Trabajador</th><th className="px-3 py-2">Creados</th><th className="px-3 py-2">Ya existían</th></tr></thead><tbody>{missingDraftResult.results.map((row) => <tr className="border-t" key={row.person_id}><td className="px-3 py-2"><p className="font-medium">{row.name}</p><p className="text-xs text-slate-500">{row.rut}</p></td><td className="px-3 py-2">{row.created.length ? row.created.map((kind) => kind === "CONTRACT" ? "Contrato" : "EPP").join(" · ") : "—"}</td><td className="px-3 py-2">{row.already_had.length ? row.already_had.map((kind) => kind === "CONTRACT" ? "Contrato" : "EPP").join(" · ") : "—"}</td></tr>)}</tbody></table></div><div className="flex justify-end"><Button onClick={() => setMissingDraftResult(null)}>Listo</Button></div></div></ModalShell>}
      {confirmSelectedBundles && <ConfirmDialog open loading={busy} title="Enviar documentos seleccionados" description={"Se pondrán en cola " + bundlePairs.filter(({ contract }) => selectedPeople.has(`${contract.person_id}:${contract.event_id || "global"}`)).length + " conjunto(s). El backend seguirá enviando un correo por trabajador aunque cierres esta página; los enlaces vigentes se reemplazarán."} confirmLabel="Guardar lote y enviar" onClose={() => setConfirmSelectedBundles(false)} onConfirm={() => void performSendSelectedBundles()}/>}
      {batchGenerationPreview && <ModalShell size="lg" title="Revisión antes de crear" description={`${batchGenerationPreview.event_name} · ${batchGenerationPreview.workers_processed} trabajadores · ${batchGenerationPreview.results.filter((row) => row.missing_data?.length).length} con datos por completar`} onClose={() => setBatchGenerationPreview(null)}><div className="space-y-4"><div className="grid gap-2 sm:grid-cols-3"><div className="rounded-lg bg-emerald-50 p-3"><p className="text-xs text-emerald-800">Contratos nuevos</p><p className="text-xl font-bold">{batchGenerationPreview.contracts_to_create}</p></div><div className="rounded-lg bg-sky-50 p-3"><p className="text-xs text-sky-800">Registros EPP nuevos</p><p className="text-xl font-bold">{batchGenerationPreview.epp_to_create}</p></div><div className="rounded-lg bg-slate-100 p-3"><p className="text-xs text-slate-600">Documentos existentes</p><p className="text-xl font-bold">{batchGenerationPreview.documents_existing}</p></div></div>{batchGenerationPreview.setup_warnings.length > 0 && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Faltan datos base de Greenway: {batchGenerationPreview.setup_warnings.join(", ")}. Se crearán borradores para completar/revisar; enviar seguirá bloqueado hasta completar los campos obligatorios.</p>}<div className="max-h-[45vh] overflow-auto rounded-lg border"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="p-2">Trabajador</th><th className="p-2">Ficha / faena</th><th className="p-2">A crear</th><th className="p-2">Preservados</th><th className="p-2">Revisión de datos</th></tr></thead><tbody>{batchGenerationPreview.results.map((row) => <tr className="border-t" key={row.rut}><td className="p-2">{row.name}<span className="block text-xs text-slate-500">{row.rut}</span></td><td className="p-2">{row.person_action} · {row.assignment_action}</td><td className="p-2">{row.create.length ? row.create.map((kind) => kind === "CONTRACT" ? "Contrato" : "EPP").join(" · ") : "Ninguno"}</td><td className="p-2">{row.already_had.length ? row.already_had.map((kind) => kind === "CONTRACT" ? "Contrato" : "EPP").join(" · ") : "—"}</td><td className="p-2 text-xs">{row.missing_data?.length ? <span className="text-amber-800">Completar: {row.missing_data.join(", ")}</span> : <span className="text-emerald-800">Sin faltantes detectados</span>}</td></tr>)}</tbody></table></div><p className="text-xs text-slate-500">No se enviarán correos. Los documentos existentes se conservan. Los borradores incompletos se pueden guardar para revisión, pero el envío exige completar sus campos.</p><div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setBatchGenerationPreview(null)}>Volver</Button><Button disabled={busy} onClick={() => void generateBatchDrafts()}>{busy ? "Creando…" : `Crear ${batchGenerationPreview.documents_to_create} borradores`}</Button></div></div></ModalShell>}
      {batchGenerationResult && <ModalShell size="lg" title="Resultado de importación y generación" description={`${batchGenerationResult.event_name} · ${batchGenerationResult.workers_processed} trabajador(es) · ${batchGenerationResult.workers_failed} con error`} onClose={() => { setBatchGenerationResult(null); if (!batchGenerationResult.workers_failed) { setImportPreview(null); setImportFile(null); } }}><div className="space-y-3"><div className="grid gap-2 sm:grid-cols-4"><div className="rounded-lg bg-emerald-50 p-3 text-sm">Personas nuevas <strong className="block text-xl">{batchGenerationResult.people_created}</strong></div><div className="rounded-lg bg-sky-50 p-3 text-sm">Actualizadas <strong className="block text-xl">{batchGenerationResult.people_updated}</strong></div><div className="rounded-lg bg-indigo-50 p-3 text-sm">Documentos creados <strong className="block text-xl">{batchGenerationResult.documents_created}</strong></div><div className="rounded-lg bg-slate-100 p-3 text-sm">Existentes conservados <strong className="block text-xl">{batchGenerationResult.documents_skipped}</strong></div></div>{batchGenerationResult.setup_warnings.length > 0 && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Completa los datos base de Greenway antes de enviar contratos: {batchGenerationResult.setup_warnings.join(", ")}.</p>}<div className="max-h-[50vh] overflow-auto rounded-lg border"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="p-2">Trabajador</th><th className="p-2">Resultado</th><th className="p-2">Documentos nuevos</th><th className="p-2">Ya existían</th></tr></thead><tbody>{batchGenerationResult.results.map((row) => <tr className="border-t" key={row.rut}><td className="p-2">{row.name}<span className="block text-xs text-slate-500">{row.rut}</span></td><td className="p-2"><span className={row.status === "ERROR" ? "font-semibold text-rose-700" : "font-semibold text-emerald-700"}>{row.status === "ERROR" ? "Error" : `${row.person_action === "created" ? "Creada" : "Actualizada"} · ${row.assignment_action === "created" ? "asignación nueva" : "asignación actualizada"}`}</span>{row.error && <span className="block text-xs text-rose-700">{row.error}</span>}</td><td className="p-2">{row.created.length ? row.created.map((kind) => kind === "CONTRACT" ? "Contrato" : "EPP").join(" · ") : "—"}</td><td className="p-2">{row.already_had.length ? row.already_had.map((kind) => kind === "CONTRACT" ? "Contrato" : "EPP").join(" · ") : "—"}</td></tr>)}</tbody></table></div><div className="flex justify-end gap-2">{batchGenerationResult.workers_failed > 0 && <Button disabled={busy} onClick={() => void retryFailedImportRows()}>{busy ? "Reintentando…" : `Reintentar solo ${batchGenerationResult.workers_failed} fallido(s)`}</Button>}<Button variant="secondary" onClick={() => { const failed = batchGenerationResult.workers_failed > 0; setBatchGenerationResult(null); if (!failed) { setImportPreview(null); setImportFile(null); } }}>Cerrar</Button></div></div></ModalShell>}
      {missingDraftPreview && <ModalShell size="lg" title="Revisar borradores faltantes" description={`${missingDraftPreview.event_name} · ${missingDraftPreview.workers_processed} persona(s) · ${missingDraftPreview.results.filter((row) => row.missing_data?.length).length} con datos por completar`} onClose={() => setMissingDraftPreview(null)}><div className="space-y-4"><div className="grid gap-2 sm:grid-cols-3"><div className="rounded-lg bg-emerald-50 p-3">Contratos a crear <strong className="block text-xl">{missingDraftPreview.contracts_to_create}</strong></div><div className="rounded-lg bg-sky-50 p-3">EPP a crear <strong className="block text-xl">{missingDraftPreview.epp_to_create}</strong></div><div className="rounded-lg bg-slate-100 p-3">Existentes <strong className="block text-xl">{missingDraftPreview.documents_existing}</strong></div></div>{missingDraftPreview.setup_warnings.length > 0 && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Faltan datos base de Greenway: {missingDraftPreview.setup_warnings.join(", ")}.</p>}<div className="max-h-[45vh] overflow-auto rounded-lg border"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="p-2">Persona</th><th className="p-2">A crear</th><th className="p-2">Se conservan</th><th className="p-2">Revisión de datos</th></tr></thead><tbody>{missingDraftPreview.results.map((row) => <tr className="border-t" key={row.person_id || row.rut}><td className="p-2">{row.name}<span className="block text-xs text-slate-500">{row.rut}</span></td><td className="p-2">{row.create.length ? row.create.join(" · ") : "—"}</td><td className="p-2">{row.already_had.length ? row.already_had.join(" · ") : "—"}</td><td className="p-2 text-xs">{row.missing_data?.length ? <span className="text-amber-800">Completar: {row.missing_data.join(", ")}</span> : <span className="text-emerald-800">Sin faltantes detectados</span>}</td></tr>)}</tbody></table></div><p className="text-xs text-slate-500">Los borradores incompletos se pueden crear y guardar para revisión; el envío seguirá bloqueado hasta corregir los campos obligatorios.</p><div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setMissingDraftPreview(null)}>Volver</Button><Button disabled={busy || missingDraftPreview.documents_to_create === 0} onClick={() => void generateMissingDrafts()}>{busy ? "Creando…" : `Crear ${missingDraftPreview.documents_to_create} borradores`}</Button></div></div></ModalShell>}
      {peopleImportResult && <ModalShell size="lg" title="Resultado de importación" description={`${peopleImportResult.workers_processed} trabajador(es) procesados · ${peopleImportResult.workers_failed} con error`} onClose={() => { const failed = peopleImportResult.workers_failed > 0; setPeopleImportResult(null); if (!failed) { setImportPreview(null); setImportFile(null); } }}><div className="space-y-3"><div className="grid gap-2 sm:grid-cols-3"><div className="rounded-lg bg-emerald-50 p-3">Personas nuevas <strong className="block text-xl">{peopleImportResult.created}</strong></div><div className="rounded-lg bg-sky-50 p-3">Personas actualizadas <strong className="block text-xl">{peopleImportResult.updated}</strong></div><div className="rounded-lg bg-slate-100 p-3">Asignaciones procesadas <strong className="block text-xl">{peopleImportResult.assignments}</strong></div></div><div className="max-h-[50vh] overflow-auto rounded-lg border"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="p-2">Trabajador</th><th className="p-2">Resultado</th><th className="p-2">Faena</th></tr></thead><tbody>{peopleImportResult.results.map((row) => <tr className="border-t" key={row.rut}><td className="p-2">{row.name}<span className="block text-xs text-slate-500">{row.rut}</span></td><td className="p-2"><span className={row.status === "ERROR" ? "font-semibold text-rose-700" : "font-semibold text-emerald-700"}>{row.status === "ERROR" ? "Error" : row.person_action === "created" ? "Persona creada" : "Persona actualizada"}</span>{row.error && <span className="block text-xs text-rose-700">{row.error}</span>}</td><td className="p-2">{row.assignment_action === "created" ? "Asignación creada" : row.assignment_action === "updated" ? "Asignación actualizada" : "Sin cambios"}</td></tr>)}</tbody></table></div><div className="flex justify-end gap-2">{peopleImportResult.workers_failed > 0 && <Button disabled={busy} onClick={() => void retryFailedPeopleImportRows()}>{busy ? "Reintentando…" : `Reintentar solo ${peopleImportResult.workers_failed} fallido(s)`}</Button>}<Button variant="secondary" onClick={() => { const failed = peopleImportResult.workers_failed > 0; setPeopleImportResult(null); if (!failed) { setImportPreview(null); setImportFile(null); } }}>Cerrar</Button></div></div></ModalShell>}
      {historyPerson && <ModalShell size="lg" title={`Historial de ${historyPerson.name}`} description={`${events.find((event) => event.id === historyPerson.eventId)?.name || "Faena"} · actividad y cambios registrados`} onClose={() => { setHistoryPerson(null); setHistoryEntries([]); }}>
        <div className="max-h-[65vh] space-y-3 overflow-y-auto">
          {historyLoading ? <div className="p-8 text-center text-slate-500"><LoaderCircle className="mx-auto h-6 w-6 animate-spin"/>Cargando historial…</div>
            : historyEntries.length === 0 ? <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">Aún no hay movimientos registrados para esta persona en esta faena.</p>
              : historyEntries.map((entry) => <article className="rounded-xl border border-slate-200 bg-white p-4" key={entry.id}>
                <div className="flex flex-wrap items-start justify-between gap-2"><p className="font-semibold text-slate-900">{historyActionLabels[entry.action] || "Actividad en documentos"}</p><time className="whitespace-nowrap text-xs text-slate-500">{new Date(entry.created_at).toLocaleString("es-CL")}</time></div>
                <p className="mt-1 text-sm text-slate-500">Realizado por {entry.actor}</p>
                {historyDetails(entry).length > 0 && <dl className="mt-3 grid gap-2 rounded-lg bg-slate-50 p-3 sm:grid-cols-2">{historyDetails(entry).map((detail, index) => <div key={`${detail.label}-${index}`}><dt className="text-xs font-medium text-slate-500">{detail.label}</dt><dd className="text-sm text-slate-800">{detail.value}</dd></div>)}</dl>}
              </article>)}
        </div>
      </ModalShell>}
      <AssignExistingPeopleModal events={events} clientId={clientQuery} open={assignExistingOpen} onClose={() => setAssignExistingOpen(false)} onDone={load}/>
      {editOptionsPerson && <ModalShell title="¿Qué quieres editar?" description={`Elige si actualizar la ficha de ${editOptionsPerson.first_name} ${editOptionsPerson.last_name} o sus datos laborales para esta faena.`} onClose={() => setEditOptionsPerson(null)}>
        <div className="space-y-3">
          {isAdmin && <button className="flex w-full items-start gap-3 rounded-lg border p-4 text-left hover:border-emerald-500 hover:bg-emerald-50" onClick={() => { const person = editOptionsPerson; setEditOptionsPerson(null); openEditPerson(person); }}><Users className="mt-0.5 h-5 w-5 text-emerald-700"/><span><strong className="block">Ficha personal</strong><span className="text-sm text-slate-600">Nombre, RUT, contacto y domicilio reutilizables.</span></span></button>}
          <button disabled={!getEmploymentSummary(editOptionsPerson)} className="flex w-full items-start gap-3 rounded-lg border p-4 text-left hover:border-emerald-500 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50" onClick={() => { const person = editOptionsPerson; setEditOptionsPerson(null); openEditEmployment(person); }}><Pencil className="mt-0.5 h-5 w-5 text-emerald-700"/><span><strong className="block">Asignación de faena</strong><span className="text-sm text-slate-600">{getEmploymentSummary(editOptionsPerson) ? `Cargo, área, fechas y remuneración para ${events.find((event) => event.id === getEmploymentSummary(editOptionsPerson)?.event_id)?.name || "esta faena"}.` : "Esta persona no tiene una asignación editable."}</span></span></button>
          <p className="rounded-lg bg-sky-50 p-3 text-xs text-sky-900">Los documentos históricos y sus enlaces no cambian al editar estos datos.</p>
        </div>
      </ModalShell>}
      {editingPerson && <ModalShell size="lg" title="Editar ficha de persona" description="Actualiza sus datos reutilizables. Las asignaciones y documentos emitidos mantienen su historial." onClose={() => setEditingPerson(null)}>
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={(event) => void savePersonProfile(event)}>
          {[["first_name", "Nombre", true], ["last_name", "Apellido", true], ["rut", "RUT", true], ["email", "Correo electrónico", false], ["phone", "Teléfono", false], ["address", "Domicilio", false], ["commune", "Comuna", false]].map(([key, label, required]) => <label className={fieldClass} key={key as string}>{label as string}<Input required={Boolean(required)} type={key === "email" ? "email" : "text"} value={personForm[key as keyof typeof personForm]} onChange={(event) => setPersonForm((current) => ({ ...current, [key as string]: event.target.value }))}/></label>)}
          <p className="rounded-lg bg-sky-50 p-3 text-sm text-sky-900 sm:col-span-2">Si la persona ya tiene documentos enviados o completados, sus PDF históricos no cambiarán. Las correcciones se usarán en nuevos documentos.</p>
          <div className="flex justify-end gap-2 sm:col-span-2"><Button type="button" variant="secondary" onClick={() => setEditingPerson(null)}>Cerrar</Button><Button disabled={busy}>{busy ? "Guardando…" : "Guardar ficha"}</Button></div>
        </form>
      </ModalShell>}
      {editingEmployment && <ModalShell size="lg" title="Editar asignación de faena" description="Los cambios se aplican solo a esta asignación; no cambian el historial de otras faenas ni documentos ya emitidos." onClose={() => setEditingEmployment(null)}>
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={(event) => void saveEmployment(event)}>
          <div className="rounded-lg bg-slate-50 p-3 text-sm sm:col-span-2"><p className="font-semibold">{editingEmployment.person.first_name} {editingEmployment.person.last_name} · {editingEmployment.person.rut}</p><p className="text-slate-600">{events.find((event) => event.id === editingEmployment.assignment.event_id)?.name || "Faena asociada"}</p></div>
          {[["position", "Cargo", true], ["duties", "Labores / funciones para el contrato (opcional)", false], ["area", "Área", false], ["workplace", "Lugar de trabajo / dependencias", false], ["start_date", "Fecha de inicio", false], ["end_date", "Fecha de término", false], ["remuneration", "Remuneración", false]].map(([key, label, required]) => <label className={fieldClass} key={key as string}>{label as string}<Input required={Boolean(required)} type={key === "start_date" || key === "end_date" ? "date" : key === "remuneration" ? "number" : "text"} value={employmentForm[key as keyof typeof employmentForm]} onChange={(event) => setEmploymentForm((current) => ({ ...current, [key as string]: event.target.value }))}/></label>)}
          <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 sm:col-span-2">La faena asociada se mantiene fija para proteger el historial. Para otro evento se crea una asignación independiente.</p>
          <div className="flex justify-end gap-2 sm:col-span-2"><Button type="button" variant="secondary" onClick={() => setEditingEmployment(null)}>Cerrar</Button><Button disabled={busy}>{busy ? "Guardando…" : "Guardar asignación"}</Button></div>
        </form>
      </ModalShell>}
      {paperPrintOpen && eventId && <PaperPrintBatchModal
        eventId={eventId}
        eventName={events.find((event) => event.id === eventId)?.name || "Faena seleccionada"}
        people={people.filter((person) => getEmploymentSummary(person)?.event_id === eventId || documents.some((doc) => doc.person_id === person.id && doc.event_id === eventId)).map((person) => ({ personId: person.id, name: `${person.first_name} ${person.last_name}`, rut: person.rut }))}
        onChanged={() => void load()}
        onClose={() => { setPaperPrintOpen(false); void load(); }}
      />}
    </div>
  </RoleGuard>;
}
