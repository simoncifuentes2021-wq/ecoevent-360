"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { CalendarDays, Camera, Download, ExternalLink, Leaf, LoaderCircle, Pencil, Plus, QrCode, Search, ShieldCheck, UserPlus, Users, XCircle } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { useToast } from "@/components/common/ToastProvider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/useAuth";
import { getEvents } from "@/lib/api/events";
import {
  createContribution,
  createOrRegisterVolunteer,
  createVolunteerActivation,
  downloadVolunteerCsv,
  getActivationQr,
  getContributionEvidenceFile,
  getVolunteerActivations,
  getVolunteerContributions,
  getVolunteerDashboard,
  getVolunteerImpact,
  getVolunteerMaterials,
  getVolunteers,
  lookupVolunteer,
  updateContribution,
  updateVolunteer,
  updateVolunteerActivation,
  uploadContributionEvidence,
  voidContribution,
} from "@/lib/api/volunteers";
import type { Event } from "@/types/event";
import type { ListResponse } from "@/types/common";
import type {
  MaterialContribution,
  RecyclableMaterial,
  RecyclingActivation,
  VolunteerDashboard,
  VolunteerListItem,
  VolunteerResolve,
} from "@/types/volunteer";
import { ActivationFormModal, ContributionForm, VolunteerFormModal } from "@/components/volunteers/VolunteerModals";
import { VolunteerDashboardPanel } from "@/components/volunteers/VolunteerDashboardPanel";
import { FieldStaffManagement } from "@/components/volunteers/FieldStaffManagement";

type Section = "dashboard" | "volunteers" | "activations" | "contributions" | "materials" | "field_staff";
const kgFormatter = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 3 });
const consentCopy = "Acepto el registro de mis datos para gestionar mi participación en esta iniciativa y recibir información asociada a mis aportes.";
const sections: Array<[Section, string]> = [["dashboard", "Resumen"], ["volunteers", "Voluntarios"], ["activations", "Activaciones"], ["contributions", "Aportes"], ["materials", "Materiales"], ["field_staff", "Personal terreno"]];

export function VolunteersActivationsModule() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [section, setSection] = useState<Section>("dashboard");
  const [events, setEvents] = useState<Event[]>([]);
  const [eventId, setEventId] = useState("");
  const [activations, setActivations] = useState<RecyclingActivation[]>([]);
  const [materials, setMaterials] = useState<RecyclableMaterial[]>([]);
  const [contributions, setContributions] = useState<MaterialContribution[]>([]);
  const [volunteers, setVolunteers] = useState<VolunteerListItem[]>([]);
  const [dashboard, setDashboard] = useState<VolunteerDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activationForm, setActivationForm] = useState(false);
  const [editingActivation, setEditingActivation] = useState<RecyclingActivation | null>(null);
  const [volunteerForm, setVolunteerForm] = useState(false);
  const [editVolunteerTarget, setEditVolunteerTarget] = useState<VolunteerListItem | null>(null);
  const [contributionTarget, setContributionTarget] = useState<VolunteerResolve | null>(null);
  const [editContribution, setEditContribution] = useState<MaterialContribution | null>(null);
  const [voidTarget, setVoidTarget] = useState<MaterialContribution | null>(null);
  const [impactTarget, setImpactTarget] = useState<VolunteerListItem | null>(null);
  const [impactData, setImpactData] = useState<Awaited<ReturnType<typeof getVolunteerImpact>> | null>(null);
  const [qrActivation, setQrActivation] = useState<RecyclingActivation | null>(null);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [evidenceImage, setEvidenceImage] = useState<string | null>(null);
  const [selectedActivationId, setSelectedActivationId] = useState("");
  const [volunteerSearch, setVolunteerSearch] = useState("");
  const [appliedVolunteerSearch, setAppliedVolunteerSearch] = useState("");
  const [contributionVolunteerSearch, setContributionVolunteerSearch] = useState("");
  const [volunteerSearchResults, setVolunteerSearchResults] = useState<VolunteerResolve[]>([]);
  const [contributionSearch, setContributionSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [voidReason, setVoidReason] = useState("");
  const [page, setPage] = useState(1);
  const [totalVolunteers, setTotalVolunteers] = useState(0);
  const [totalContributions, setTotalContributions] = useState(0);

  const canManage = user?.role === "SUPER_ADMIN" || user?.role === "ADMIN" || user?.role === "SUPERVISOR";
  const canConfigureMaterials = user?.role === "SUPER_ADMIN" || user?.role === "ADMIN";
  const activeActivations = useMemo(() => activations.filter((item) => item.status === "ACTIVE"), [activations]);
  const selectedActivation = activations.find((item) => item.id === selectedActivationId) || null;

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getEvents({ page: 1, limit: 100 });
      setEvents(response.items);
      const remembered = typeof window !== "undefined" ? window.localStorage.getItem("eco-volunteers-event") : null;
      const nextId = response.items.some((event) => event.id === remembered) ? remembered! : response.items[0]?.id || "";
      setEventId(nextId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudieron cargar los eventos.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadData = useCallback(async () => {
    if (!eventId) {
      setActivations([]); setMaterials([]); setContributions([]); setVolunteers([]); setDashboard(null);
      return;
    }
    setLoadingData(true);
    setError(null);
    try {
      const [activationRows, materialRows, stats, contributionRows, volunteerRows] = await Promise.all([
        getVolunteerActivations(eventId),
        getVolunteerMaterials(eventId),
        getVolunteerDashboard(eventId, { date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined, date_to: dateTo ? `${dateTo}T23:59:59` : undefined }),
        getVolunteerContributions(eventId, { activation_id: selectedActivationId || undefined, status: statusFilter || undefined, date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined, date_to: dateTo ? `${dateTo}T23:59:59` : undefined, page, limit: 30 }),
        getVolunteers(eventId, { search: appliedVolunteerSearch || undefined, status: statusFilter && section === "volunteers" ? statusFilter : undefined, activation_id: selectedActivationId || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined, page, limit: 30 }),
      ]);
      setActivations(activationRows);
      setMaterials(materialRows);
      setDashboard(stats);
      setContributions(contributionRows.items);
      setTotalContributions(contributionRows.total);
      setVolunteers(volunteerRows.items);
      setTotalVolunteers(volunteerRows.total);
      if (!selectedActivationId && activationRows.length) {
        setSelectedActivationId(activationRows.find((item) => item.status === "ACTIVE")?.id || activationRows[0].id);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo actualizar la información de voluntariado.");
    } finally {
      setLoadingData(false);
    }
  }, [eventId, dateFrom, dateTo, selectedActivationId, statusFilter, page, appliedVolunteerSearch, section]);

  useEffect(() => { void loadEvents(); }, [loadEvents]);
  useEffect(() => {
    if (eventId) window.localStorage.setItem("eco-volunteers-event", eventId);
    void loadData();
  }, [eventId, loadData]);

  async function submitActivation(data: Parameters<typeof createVolunteerActivation>[0]) {
    setSaving(true);
    try {
      if (editingActivation) await updateVolunteerActivation(editingActivation.id, data);
      else await createVolunteerActivation(data);
      const wasEditing = Boolean(editingActivation);
      setActivationForm(false);
      setEditingActivation(null);
      toast({ tone: "success", title: wasEditing ? "Activación actualizada" : "Activación creada", description: wasEditing ? "Se guardaron los cambios." : "Quedó como borrador. Actívala cuando quieras abrir la inscripción." });
      await loadData();
    } catch (reason) {
      toast({ tone: "error", title: "No se pudo guardar la activación", description: messageOf(reason) });
    } finally { setSaving(false); }
  }

  async function saveVolunteerRecord(data: { full_name: string; email: string; phone: string | null; organization: string | null; status: VolunteerListItem["status"] }) {
    if (!editVolunteerTarget) return;
    setSaving(true);
    try {
      await updateVolunteer(eventId, editVolunteerTarget.id, data);
      setEditVolunteerTarget(null);
      toast({ tone: "success", title: "Ficha actualizada", description: "Los datos del voluntario se guardaron." });
      await loadData();
    } catch (reason) {
      toast({ tone: "error", title: "No se pudo actualizar la ficha", description: messageOf(reason) });
    } finally { setSaving(false); }
  }

  async function changeActivationStatus(activation: RecyclingActivation, status: RecyclingActivation["status"]) {
    try {
      await updateVolunteerActivation(activation.id, { status });
      toast({ tone: "success", title: "Estado actualizado", description: `${activation.name}: ${activationStatusLabel(status)}.` });
      await loadData();
    } catch (reason) {
      toast({ tone: "error", title: "No se pudo actualizar", description: messageOf(reason) });
    }
  }

  async function searchVolunteer() {
    const query = contributionVolunteerSearch.trim();
    if (!query || !selectedActivationId) return;
    setLoadingData(true);
    try {
      const [local, global] = await Promise.all([
        getVolunteers(eventId, { search: query, activation_id: selectedActivationId, page: 1, limit: 8 }),
        lookupVolunteer(selectedActivationId, query).catch(() => null),
      ]);
      const mapped: VolunteerResolve[] = local.items.map((item) => ({ id: item.id, full_name: item.full_name, unique_code: item.unique_code, already_in_activation: true, total_weight_kg_in_event: item.total_weight_kg }));
      if (global && !mapped.some((item) => item.id === global.id)) mapped.unshift(global);
      setVolunteerSearchResults(mapped);
      if (!mapped.length) setVolunteerForm(true);
    } catch (reason) {
      toast({ tone: "error", title: "No se pudo buscar", description: messageOf(reason) });
    } finally { setLoadingData(false); }
  }

  function searchVolunteerDirectory() {
    const query = volunteerSearch.trim();
    setPage(1);
    if (query === appliedVolunteerSearch) void loadData();
    else setAppliedVolunteerSearch(query);
  }

  async function saveVolunteer(data: Parameters<typeof createOrRegisterVolunteer>[1]) {
    if (!selectedActivationId) return;
    setSaving(true);
    try {
      const volunteer = await createOrRegisterVolunteer(selectedActivationId, data);
      setVolunteerForm(false);
      setVolunteerSearchResults([volunteer]);
      setContributionTarget(volunteer);
      toast({ tone: "success", title: volunteer.already_in_activation ? "Voluntario identificado" : "Voluntario registrado", description: "La ficha se vinculó a esta activación con su consentimiento." });
      await loadData();
    } catch (reason) {
      toast({ tone: "error", title: "No se pudo registrar al voluntario", description: messageOf(reason) });
    } finally { setSaving(false); }
  }

  async function saveContribution(data: Parameters<typeof createContribution>[1], image: File | null) {
    if (!selectedActivationId || !contributionTarget) return;
    setSaving(true);
    let created: MaterialContribution | null = null;
    try {
      created = editContribution
        ? await updateContribution(editContribution.id, { items: data.items, notes: data.notes })
        : await createContribution(selectedActivationId, data);
      if (image && !editContribution) {
        try {
          await uploadContributionEvidence(created.id, image, `Evidencia de la entrega de ${created.volunteer_name}`);
        } catch (reason) {
          toast({ tone: "error", title: "Aporte guardado; falta la foto", description: messageOf(reason) });
        }
      }
      setContributionTarget(null); setEditContribution(null);
      if (!image || editContribution) toast({ tone: "success", title: editContribution ? "Entrega corregida" : "Aporte registrado", description: `Total: ${kg(created.total_weight_kg)}. El acumulado del evento se recalculó.` });
      await loadData();
    } catch (reason) {
      toast({ tone: "error", title: "No se pudo guardar el aporte", description: messageOf(reason) });
    } finally { setSaving(false); }
  }

  async function confirmVoid() {
    if (!voidTarget || voidReason.trim().length < 5) return;
    setSaving(true);
    try {
      await voidContribution(voidTarget.id, voidReason.trim());
      setVoidTarget(null); setVoidReason("");
      toast({ tone: "success", title: "Entrega anulada", description: "Se conserva en el historial y ya no suma en las métricas." });
      await loadData();
    } catch (reason) { toast({ tone: "error", title: "No se pudo anular", description: messageOf(reason) }); }
    finally { setSaving(false); }
  }

  async function showImpact(volunteer: VolunteerListItem) {
    setImpactTarget(volunteer); setImpactData(null);
    try { setImpactData(await getVolunteerImpact(eventId, volunteer.id)); }
    catch (reason) { toast({ tone: "error", title: "No se pudo cargar el historial", description: messageOf(reason) }); setImpactTarget(null); }
  }

  async function showQr(activation: RecyclingActivation) {
    setQrActivation(activation); setQrUrl(null);
    try { const blob = await getActivationQr(activation.id); setQrUrl(URL.createObjectURL(blob)); }
    catch (reason) { setQrActivation(null); toast({ tone: "error", title: "No se pudo generar el QR", description: messageOf(reason) }); }
  }

  async function exportCsv() {
    try {
      const blob = await downloadVolunteerCsv(eventId, selectedActivationId || undefined);
      const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
      anchor.href = url; anchor.download = "aportes-reciclaje.csv"; anchor.click(); URL.revokeObjectURL(url);
      toast({ tone: "success", title: "Archivo descargado", description: "El CSV contiene los aportes filtrados." });
    } catch (reason) { toast({ tone: "error", title: "No se pudo exportar", description: messageOf(reason) }); }
  }

  async function openEvidence(contribution: MaterialContribution) {
    await openEvidenceById(contribution.id);
  }

  async function openEvidenceById(contributionId: string, evidenceId?: string) {
    try {
      const rows = await (await import("@/lib/api/volunteers")).listContributionEvidence(contributionId);
      if (!rows.length) throw new Error("Esta entrega todavía no tiene fotos.");
      const selected = evidenceId ? rows.find((row) => row.id === evidenceId) : rows[0];
      if (!selected) throw new Error("No encontramos esa evidencia.");
      const blob = await getContributionEvidenceFile(contributionId, selected.id);
      setEvidenceImage(URL.createObjectURL(blob));
    } catch (reason) { toast({ tone: "error", title: "No se pudo abrir la evidencia", description: messageOf(reason) }); }
  }

  if (loading) return <LoadingState label="Cargando Voluntarios y Activaciones..." />;
  if (error && !events.length) return <ErrorState message={error} onRetry={loadEvents} />;

  return <div className="space-y-5">
    <PageHeader eyebrow="Impacto circular" title="Voluntarios y Activaciones" description="Organiza puntos de recolección y sigue cada aporte sin duplicar fichas ni alterar los registros ambientales existentes." actions={canManage ? <Button onClick={() => { setEditingActivation(null); setActivationForm(true); }}><Plus className="h-4 w-4" />Nueva activación</Button> : undefined} />

    <section className="grid min-w-0 gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-[minmax(18rem,1fr)_minmax(0,1.3fr)] md:items-end">
      <label className="grid min-w-0 gap-1.5 text-sm font-semibold text-slate-700">Evento<select className="h-11 min-w-0 w-full rounded-xl border border-slate-200 bg-white px-3" value={eventId} onChange={(e) => { setEventId(e.target.value); setPage(1); }}><option value="">Selecciona un evento</option>{events.map((event) => <option key={event.id} value={event.id}>{event.name}</option>)}</select></label>
      <div className="grid min-w-0 gap-1.5"><span className="text-sm font-semibold text-slate-700">Período</span><div className="flex min-w-0 flex-wrap items-center gap-2 text-sm text-slate-500"><label className="flex min-w-0 flex-1 items-center gap-2">Desde<input aria-label="Fecha desde" className="h-11 min-w-0 w-full rounded-xl border border-slate-200 px-2" type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} /></label><span aria-hidden="true">a</span><label className="flex min-w-0 flex-1 items-center gap-2">Hasta<input aria-label="Fecha hasta" className="h-11 min-w-0 w-full rounded-xl border border-slate-200 px-2" type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} /></label></div></div>
    </section>

    <div className="flex gap-2 overflow-x-auto border-b border-slate-200 pb-2" role="tablist" aria-label="Secciones de voluntariado">
      {sections.filter(([key]) => !["materials", "field_staff"].includes(key) || canConfigureMaterials).map(([key, label]) => <Button aria-selected={section === key} key={key} role="tab" variant={section === key ? "primary" : "secondary"} onClick={() => { setSection(key); setPage(1); }}>{label}{key === "activations" ? ` (${activations.length})` : key === "volunteers" ? ` (${totalVolunteers})` : key === "contributions" ? ` (${totalContributions})` : ""}</Button>)}
      <span className="flex-1" /><Button aria-label="Actualizar información" disabled={loadingData || !eventId} variant="secondary" onClick={() => void loadData()}>{loadingData ? <LoaderCircle className="h-4 w-4 animate-spin" /> : "Actualizar"}</Button>
    </div>

    {error ? <ErrorState message={error} onRetry={loadData} /> : null}
    {loadingData && !error ? <LoadingState label="Actualizando los datos del evento..." /> : null}
    {!eventId ? <EmptyState title="No hay eventos disponibles" description="Los eventos que puedes gestionar aparecerán aquí." /> : null}

    {eventId && !loadingData && section === "dashboard" ? <VolunteerDashboardPanel data={dashboard} /> : null}
    {eventId && section === "activations" ? <ActivationSection items={activations} materials={materials} canManage={canManage} onEdit={(activation) => { setEditingActivation(activation); setActivationForm(true); }} onStatus={changeActivationStatus} onQr={showQr} onRegister={(activation) => { setSelectedActivationId(activation.id); setSection("contributions"); setContributionVolunteerSearch(""); setVolunteerSearchResults([]); setContributionTarget(null); }} onCopy={(activation) => { void navigator.clipboard.writeText(`${window.location.origin}/public/inscripcion-voluntarios/${activation.public_slug}`).then(() => toast({ tone: "success", title: "Enlace copiado", description: "Puedes compartirlo o imprimir su QR." })); }} /> : null}
    {eventId && section === "contributions" ? <ContributionSection activations={activations} materials={materials} items={contributions} total={totalContributions} page={page} search={contributionSearch} setSearch={setContributionSearch} setPage={setPage} statusFilter={statusFilter} setStatusFilter={setStatusFilter} selectedActivationId={selectedActivationId} setSelectedActivationId={setSelectedActivationId} onSearch={searchVolunteer} searchResults={volunteerSearchResults} searchQuery={contributionVolunteerSearch} setSearchQuery={setContributionVolunteerSearch} onChoose={setContributionTarget} onNewVolunteer={() => setVolunteerForm(true)} onEdit={(item) => { setEditContribution(item); setContributionTarget({ id: item.volunteer_id, full_name: item.volunteer_name, unique_code: item.volunteer_code, already_in_activation: true, total_weight_kg_in_event: item.total_weight_kg }); }} onVoid={setVoidTarget} onEvidence={openEvidence} canManage={canManage} onExport={exportCsv} /> : null}
    {eventId && section === "volunteers" ? <VolunteersSection items={volunteers} total={totalVolunteers} page={page} setPage={setPage} search={volunteerSearch} setSearch={setVolunteerSearch} statusFilter={statusFilter} setStatusFilter={setStatusFilter} canManage={canManage} onSearch={searchVolunteerDirectory} onImpact={showImpact} onEdit={setEditVolunteerTarget} /> : null}
    {eventId && !loadingData && section === "materials" && canConfigureMaterials ? <MaterialsSection items={materials} /> : null}
    {eventId && section === "field_staff" && canConfigureMaterials ? <FieldStaffManagement eventId={eventId} activations={activations} /> : null}

    {totalVolunteers > 30 && section === "volunteers" ? <Pagination page={page} total={totalVolunteers} onPage={setPage} /> : null}
    {totalContributions > 30 && section === "contributions" ? <Pagination page={page} total={totalContributions} onPage={setPage} /> : null}

    {activationForm && eventId ? <ActivationFormModal eventId={eventId} materials={materials} initial={editingActivation || undefined} onClose={() => { setActivationForm(false); setEditingActivation(null); }} onSave={submitActivation} saving={saving} /> : null}
    {volunteerForm && selectedActivationId ? <VolunteerFormModal initialEmail={contributionVolunteerSearch.includes("@") ? contributionVolunteerSearch : undefined} consentText={consentCopy} onClose={() => setVolunteerForm(false)} onSave={saveVolunteer} saving={saving} /> : null}
    {editVolunteerTarget ? <VolunteerEditModal volunteer={editVolunteerTarget} saving={saving} onClose={() => setEditVolunteerTarget(null)} onSave={saveVolunteerRecord} /> : null}
    {contributionTarget && selectedActivationId ? <ContributionForm activationId={selectedActivationId} materials={materials} volunteer={contributionTarget} initial={editContribution || undefined} onCancel={() => { setContributionTarget(null); setEditContribution(null); }} onSave={saveContribution} saving={saving} /> : null}
    {voidTarget ? <ModalShell title="Anular entrega" description="La entrega seguirá en el historial, pero dejará de contar en las métricas." onClose={() => { setVoidTarget(null); setVoidReason(""); }}><form className="space-y-4" onSubmit={(e) => { e.preventDefault(); void confirmVoid(); }}><label className="grid gap-1 text-sm font-semibold">Motivo de anulación<textarea className="min-h-24 rounded-xl border p-3" minLength={5} required value={voidReason} onChange={(e) => setVoidReason(e.target.value)} /></label><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setVoidTarget(null)}>Volver</Button><Button variant="destructive" disabled={saving || voidReason.trim().length < 5}>Confirmar anulación</Button></div></form></ModalShell> : null}
    {impactTarget ? <ImpactModal volunteer={impactTarget} data={impactData} onEvidence={openEvidenceById} onClose={() => { setImpactTarget(null); setImpactData(null); }} /> : null}
    {qrActivation ? <QrModal activation={qrActivation} url={qrUrl} onClose={() => { setQrActivation(null); if (qrUrl) URL.revokeObjectURL(qrUrl); setQrUrl(null); }} /> : null}
    {evidenceImage ? <ModalShell title="Foto de evidencia" onClose={() => { URL.revokeObjectURL(evidenceImage); setEvidenceImage(null); }}><Image alt="Evidencia fotográfica del aporte" className="mx-auto h-auto max-h-[70vh] w-auto rounded-xl object-contain" height={1200} unoptimized src={evidenceImage} width={1600} /></ModalShell> : null}
  </div>;
}

function ActivationSection({ items, materials, canManage, onEdit, onStatus, onQr, onRegister, onCopy }: {
  items: RecyclingActivation[]; materials: RecyclableMaterial[]; canManage: boolean;
  onEdit: (item: RecyclingActivation) => void;
  onStatus: (item: RecyclingActivation, status: RecyclingActivation["status"]) => void;
  onQr: (item: RecyclingActivation) => void; onRegister: (item: RecyclingActivation) => void; onCopy: (item: RecyclingActivation) => void;
}) {
  if (!items.length) return <EmptyState title="Aún no hay activaciones" description="Crea una activación para definir dónde y cuándo recibirán materiales." />;
  return <div className="grid gap-3 xl:grid-cols-2">{items.map((item) => <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" key={item.id}>
    <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h2 className="text-lg font-bold text-slate-950">{item.name}</h2><StatusPill status={item.status} /></div><p className="mt-1 text-sm text-slate-500">{item.event_name} · {item.location_name || "Ubicación por definir"}</p></div><p className="text-right text-sm font-semibold text-emerald-800">{kg(item.total_weight_kg)}<span className="block text-xs font-normal text-slate-500">recuperados</span></p></div>
    <div className="mt-4 grid grid-cols-3 gap-2 text-center"><MiniMetric label="Voluntarios" value={item.volunteer_count} /><MiniMetric label="Entregas" value={item.contribution_count} /><MiniMetric label="Estado" value={activationStatusLabel(item.status)} /></div><div className="mt-3 flex flex-wrap gap-1.5">{item.allowed_material_ids.map((id) => { const material = materials.find((row) => row.id === id); return material ? <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800" key={id}>{material.name}</span> : null; })}{!item.allowed_material_ids.length ? <span className="text-xs text-amber-700">Sin materiales configurados</span> : null}</div>
    <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t pt-4"><div className="text-xs text-slate-500"><p>{formatDate(item.starts_at)}</p><p>{item.address || item.location_name || "Lugar pendiente"}</p></div><div className="flex flex-wrap gap-2">
      {item.status === "ACTIVE" ? <><Button size="sm" variant="secondary" onClick={() => onRegister(item)}><Plus className="h-4 w-4" />Registrar aporte</Button><Button size="sm" variant="secondary" onClick={() => onQr(item)}><QrCode className="h-4 w-4" />QR</Button><Button size="sm" variant="secondary" onClick={() => onCopy(item)}><ExternalLink className="h-4 w-4" />Copiar enlace</Button>{canManage ? <Button size="sm" variant="ghost" onClick={() => onStatus(item, "CLOSED")}>Cerrar</Button> : null}</> : null}
      {canManage && item.status !== "ARCHIVED" ? <Button size="sm" variant="ghost" onClick={() => onEdit(item)}><Pencil className="h-4 w-4" />Editar</Button> : null}
      {canManage && item.status === "DRAFT" ? <Button size="sm" onClick={() => onStatus(item, "ACTIVE")}>Activar inscripción</Button> : null}
      {canManage && item.status === "CLOSED" ? <Button size="sm" variant="secondary" onClick={() => onStatus(item, "ACTIVE")}>Reabrir</Button> : null}
    </div></div>
  </article>)}</div>;
}

function ContributionSection(props: {
  activations: RecyclingActivation[]; materials: RecyclableMaterial[]; items: MaterialContribution[]; total: number; page: number;
  search: string; setSearch: (value: string) => void; setPage: (value: number) => void; statusFilter: string; setStatusFilter: (value: string) => void;
  selectedActivationId: string; setSelectedActivationId: (value: string) => void; onSearch: () => void;
  searchResults: VolunteerResolve[]; searchQuery: string; setSearchQuery: (value: string) => void; onChoose: (value: VolunteerResolve) => void;
  onNewVolunteer: () => void; onEdit: (item: MaterialContribution) => void; onVoid: (item: MaterialContribution) => void; onEvidence: (item: MaterialContribution) => void;
  canManage: boolean; onExport: () => void;
}) {
  const selected = props.activations.find((activation) => activation.id === props.selectedActivationId);
  return <div className="space-y-4">
    {selected?.status === "ACTIVE" ? <section className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-4 sm:p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wider text-emerald-800">Registro rápido en terreno</p><h2 className="mt-1 text-lg font-bold">{selected.name}</h2><p className="text-sm text-slate-600">Busca una persona del evento o identifícala por correo, teléfono o código.</p></div><label className="grid gap-1 text-xs font-semibold text-slate-600">Activación<select className="h-10 min-w-56 rounded-lg border bg-white px-3 text-sm" value={props.selectedActivationId} onChange={(e) => props.setSelectedActivationId(e.target.value)}>{props.activations.filter((item) => item.status === "ACTIVE").map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div>
      <div className="mt-4 flex flex-col gap-2 sm:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><Input className="h-11 pl-9" placeholder="Nombre, correo, teléfono o código VOL-..." value={props.searchQuery} onChange={(e) => props.setSearchQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); props.onSearch(); } }} /></div><Button className="h-11" disabled={!props.searchQuery.trim()} onClick={props.onSearch}><Search className="h-4 w-4" />Buscar persona</Button><Button className="h-11" variant="secondary" onClick={props.onNewVolunteer}><UserPlus className="h-4 w-4" />Registrar voluntario</Button></div>
      {props.searchResults.length ? <div className="mt-3 grid gap-2 sm:grid-cols-2">{props.searchResults.map((person) => <button className="flex items-center justify-between gap-3 rounded-xl border bg-white p-3 text-left hover:border-emerald-400" key={person.id} onClick={() => props.onChoose(person)} type="button"><span><strong className="block text-sm">{person.full_name}</strong><span className="text-xs text-slate-500">{person.unique_code} · {person.already_in_activation ? "Inscrito en esta activación" : "Ficha existente; se vinculará a esta activación"}</span></span><span className="text-right text-sm font-semibold text-emerald-800">{kg(person.total_weight_kg_in_event)}<small className="block text-xs font-normal text-slate-500">en este evento</small></span></button>)}</div> : null}
      {props.searchQuery.trim().length >= 3 && !props.searchResults.length ? <p className="mt-3 rounded-lg bg-white/80 p-3 text-sm text-slate-600">Sin coincidencias todavía. Puedes buscar por nombre dentro de este evento o registrar una ficha nueva.</p> : null}
    </section> : <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">Selecciona una activación activa para registrar nuevas entregas.</div>}
    <div className="flex flex-col gap-3 rounded-2xl border bg-white p-4 shadow-sm lg:flex-row lg:items-end">
      <label className="grid gap-1 text-sm font-semibold">Filtrar activación<select className="h-10 rounded-lg border px-3" value={props.selectedActivationId} onChange={(e) => props.setSelectedActivationId(e.target.value)}><option value="">Todas las activaciones</option>{props.activations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <label className="grid gap-1 text-sm font-semibold">Estado<select className="h-10 rounded-lg border px-3" value={props.statusFilter} onChange={(e) => { props.setStatusFilter(e.target.value); props.setPage(1); }}><option value="">Todos</option><option value="ACTIVE">Vigentes</option><option value="VOID">Anulados</option></select></label>
      <label className="grid min-w-48 gap-1 text-sm font-semibold">Buscar en esta página<Input className="h-10" placeholder="Persona o material" value={props.search} onChange={(e) => props.setSearch(e.target.value)} /></label>
      <span className="flex-1" /><Button variant="secondary" onClick={props.onExport}><Download className="h-4 w-4" />Exportar CSV</Button>
    </div>
    {!props.items.length ? <EmptyState title="No hay entregas registradas" description="Cuando se guarde un aporte, aparecerá aquí con sus materiales, peso, encargado y evidencia." /> : null}
    <div className="grid gap-3">{props.items.filter((item) => !props.search || `${item.volunteer_name} ${item.volunteer_code} ${item.items.map((row) => row.material_name_snapshot).join(" ")}`.toLowerCase().includes(props.search.toLowerCase())).map((item) => <article className={`rounded-2xl border bg-white p-4 shadow-sm ${item.status === "VOID" ? "border-rose-200 opacity-80" : "border-slate-200"}`} key={item.id}>
      <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex flex-wrap items-center gap-2"><h3 className="font-bold">{item.volunteer_name}</h3><span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{item.volunteer_code}</span><StatusPill status={item.status} /></div><p className="mt-1 text-sm text-slate-500">{item.activation_name} · {formatDate(item.registered_at)} · {item.registered_by_name || "Registro de terreno"}</p></div><div className="text-right"><p className="text-xl font-bold text-emerald-800">{kg(item.total_weight_kg)}</p><p className="text-xs text-slate-500">Correo: {emailStatus(item.email_status)}</p></div></div>
      <div className="mt-3 flex flex-wrap gap-2">{item.items.map((row) => <span className="rounded-lg bg-slate-50 px-3 py-2 text-sm" key={row.id || row.material_id}><strong>{row.material_name_snapshot}</strong><span className="ml-2 text-slate-600">{kg(row.weight_kg)}</span></span>)}</div>
      {item.void_reason ? <p className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">Motivo de anulación: {item.void_reason}</p> : null}
      <div className="mt-3 flex flex-wrap justify-end gap-2 border-t pt-3">{item.evidence_count ? <Button size="sm" variant="secondary" onClick={() => props.onEvidence(item)}><Camera className="h-4 w-4" />Ver evidencia ({item.evidence_count})</Button> : null}{props.canManage && item.status === "ACTIVE" ? <><Button size="sm" variant="secondary" onClick={() => props.onEdit(item)}><Pencil className="h-4 w-4" />Corregir</Button><Button size="sm" variant="ghost" onClick={() => props.onVoid(item)}><XCircle className="h-4 w-4" />Anular</Button></> : null}</div>
    </article>)}</div>
    {props.total > 30 ? <Pagination page={props.page} total={props.total} onPage={props.setPage} /> : null}
  </div>;
}

function VolunteersSection({ items, total, page, setPage, search, setSearch, statusFilter, setStatusFilter, canManage, onSearch, onImpact, onEdit }: {
  items: VolunteerListItem[]; total: number; page: number; setPage: (page: number) => void; search: string; setSearch: (value: string) => void;
  statusFilter: string; setStatusFilter: (value: string) => void; canManage: boolean; onSearch: () => void; onImpact: (item: VolunteerListItem) => void; onEdit: (item: VolunteerListItem) => void;
}) {
  return <div className="space-y-4">
    <section className="flex flex-col gap-3 rounded-2xl border bg-white p-4 shadow-sm sm:flex-row sm:items-end"><label className="grid flex-1 gap-1 text-sm font-semibold">Buscar por nombre, correo, teléfono o código<Input className="h-11" value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") onSearch(); }} /></label><label className="grid gap-1 text-sm font-semibold">Estado<select className="h-11 rounded-xl border px-3" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="">Todos</option><option value="ACTIVE">Activo</option><option value="INACTIVE">Inactivo</option><option value="ARCHIVED">Archivado</option></select></label><Button className="h-11" onClick={onSearch}><Search className="h-4 w-4" />Buscar</Button></section>
    {!items.length ? <EmptyState title="No encontramos voluntarios" description="Regístralos desde la inscripción pública o mientras registras una entrega." /> : <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{items.map((item) => <article className="rounded-2xl border bg-white p-4 shadow-sm" key={item.id}><div className="flex items-start justify-between gap-3"><div><h3 className="font-bold text-slate-950">{item.full_name}</h3><p className="mt-0.5 text-xs text-slate-500">{item.unique_code}</p></div><StatusPill status={item.status} /></div><div className="mt-3 space-y-1 text-sm text-slate-600">{item.email ? <p className="break-all">{item.email}</p> : <p>Correo protegido para este perfil</p>}{item.phone ? <p>{item.phone}</p> : null}<p>{item.organization || "Sin organización"}</p></div><div className="mt-4 grid grid-cols-3 gap-2 rounded-xl bg-slate-50 p-3 text-center"><MiniMetric label="Activaciones" value={item.activation_count} /><MiniMetric label="Entregas" value={item.contribution_count} /><MiniMetric label="Total evento" value={kg(item.total_weight_kg)} /></div><div className="mt-3 flex justify-end gap-2">{canManage ? <><Button size="sm" variant="secondary" onClick={() => onImpact(item)}>Historial</Button><Button aria-label={`Editar a ${item.full_name}`} size="sm" variant="ghost" onClick={() => onEdit(item)}><Pencil className="h-4 w-4" /></Button></> : null}</div></article>)}</div>}
    {total > 30 ? <Pagination page={page} total={total} onPage={setPage} /> : null}
  </div>;
}

function MaterialsSection({ items }: { items: RecyclableMaterial[] }) {
  return <section className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-white p-4">
      <div><h2 className="font-bold">Materiales reciclables disponibles</h2><p className="text-sm text-slate-500">Se muestran los tipos del catálogo de Residuos marcados como reciclables. Los aportes se registran en kg.</p></div>
      <a className="inline-flex h-10 items-center rounded-xl border border-slate-200 px-4 text-sm font-semibold hover:bg-slate-50" href="/admin/residuos/tipos">Administrar tipos de residuos</a>
    </div>
    {!items.length ? <EmptyState title="No hay tipos reciclables disponibles" description="Desde Residuos → Tipos, marca como reciclables los materiales que quieres aceptar." /> : <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{items.map((item) => <article className="rounded-2xl border bg-white p-4" key={item.id}><h3 className="font-semibold">{item.name}</h3>{item.description ? <p className="mt-1 text-sm text-slate-500">{item.description}</p> : null}<span className="mt-3 inline-block rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700">Reciclable</span></article>)}</div>}
  </section>;
}

function VolunteerEditModal({ volunteer, saving, onClose, onSave }: {
  volunteer: VolunteerListItem;
  saving: boolean;
  onClose: () => void;
  onSave: (data: { full_name: string; email: string; phone: string | null; organization: string | null; status: VolunteerListItem["status"] }) => void;
}) {
  const [fullName, setFullName] = useState(volunteer.full_name);
  const [email, setEmail] = useState(volunteer.email || "");
  const [phone, setPhone] = useState(volunteer.phone || "");
  const [organization, setOrganization] = useState(volunteer.organization || "");
  const [status, setStatus] = useState<VolunteerListItem["status"]>(volunteer.status);
  return <ModalShell title="Editar ficha del voluntario" description="La ficha se comparte entre sus activaciones. El historial y las entregas se conservan." onClose={onClose}>
    <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); onSave({ full_name: fullName.trim(), email: email.trim(), phone: phone.trim() || null, organization: organization.trim() || null, status }); }}>
      <label className="grid gap-1.5 text-sm font-medium">Nombre completo<Input autoComplete="name" maxLength={180} minLength={2} required value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
      <label className="grid gap-1.5 text-sm font-medium">Correo electrónico<Input autoComplete="email" maxLength={254} required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <label className="grid gap-1.5 text-sm font-medium">Teléfono<Input autoComplete="tel" maxLength={40} type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
      <label className="grid gap-1.5 text-sm font-medium">Organización<Input maxLength={180} value={organization} onChange={(event) => setOrganization(event.target.value)} /></label>
      <label className="grid gap-1.5 text-sm font-medium">Estado<select className="h-11 rounded-xl border bg-white px-3" value={status} onChange={(event) => setStatus(event.target.value as VolunteerListItem["status"])}><option value="ACTIVE">Activo</option><option value="INACTIVE">Inactivo</option><option value="ARCHIVED">Archivado</option></select></label>
      <div className="flex flex-col-reverse justify-end gap-2 border-t pt-4 sm:flex-row"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={saving || !fullName.trim() || !email.trim()}>{saving ? "Guardando…" : "Guardar cambios"}</Button></div>
    </form>
  </ModalShell>;
}

function ImpactModal({ volunteer, data, onEvidence, onClose }: { volunteer: VolunteerListItem; data: Awaited<ReturnType<typeof getVolunteerImpact>> | null; onEvidence: (contributionId: string, evidenceId?: string) => void; onClose: () => void }) {
  return <ModalShell title={`Historial de ${volunteer.full_name}`} description="Resumen acotado al evento seleccionado." onClose={onClose} size="lg">{!data ? <LoadingState label="Cargando el historial..." /> : <div className="space-y-4"><div className="grid gap-3 sm:grid-cols-4"><ImpactStat label="Total del evento" value={kg(data.total_weight_kg)} /><ImpactStat label="Activaciones" value={data.activation_count} /><ImpactStat label="Entregas" value={data.contribution_count} /><ImpactStat label="Código" value={data.unique_code} /></div><div className="flex flex-wrap gap-2">{Object.entries(data.material_totals).map(([material, value]) => <span className="rounded-lg bg-emerald-50 px-3 py-2 text-sm" key={material}><b>{material}</b> · {kg(value)}</span>)}</div><div className="max-h-[45vh] space-y-3 overflow-y-auto">{data.contributions.length ? data.contributions.map((contribution, index) => <article className="rounded-xl border p-4" key={contribution.id || `${contribution.registered_at}-${index}`}><div className="flex justify-between gap-2"><strong>{contribution.activation}</strong><span className="text-sm text-slate-500">{formatDate(contribution.registered_at)}</span></div><div className="mt-2 flex flex-wrap gap-2">{contribution.items.map((item, itemIndex) => <span className="text-sm text-slate-600" key={itemIndex}>{item.material}: {kg(item.weight_kg)}</span>)}</div><p className="mt-2 text-right font-bold">{kg(contribution.total_weight_kg)}</p>{contribution.evidences?.length ? <div className="mt-3 flex flex-wrap gap-2 border-t pt-3">{contribution.evidences.map((evidence, evidenceIndex) => <Button key={evidence.id} size="sm" variant="secondary" onClick={() => onEvidence(contribution.id, evidence.id)}>Ver evidencia{contribution.evidences.length > 1 ? ` ${evidenceIndex + 1}` : ""}</Button>)}</div> : null}</article>) : <p className="py-8 text-center text-sm text-slate-500">Aún no hay aportes válidos.</p>}</div></div>}</ModalShell>;
}

function QrModal({ activation, url, onClose }: { activation: RecyclingActivation; url: string | null; onClose: () => void }) {
  return <ModalShell title="QR de inscripción" description={`Escanea para inscribirte en ${activation.name}.`} onClose={onClose}><div className="grid place-items-center">{url ? <Image alt={`Código QR de inscripción para ${activation.name}`} className="h-64 w-64 rounded-xl border p-2" height={256} src={url} unoptimized width={256} /> : <div className="grid h-64 w-64 place-items-center rounded-xl bg-slate-50"><LoaderCircle className="h-8 w-8 animate-spin text-emerald-700" /></div>}<p className="mt-3 break-all text-center text-xs text-slate-500">{typeof window !== "undefined" ? `${window.location.origin}/public/inscripcion-voluntarios/${activation.public_slug}` : ""}</p><div className="mt-4 flex gap-2"><a className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-semibold text-white" download={`qr-${activation.public_slug}.png`} href={url || undefined}>Descargar QR</a><Button variant="secondary" onClick={onClose}>Cerrar</Button></div></div></ModalShell>;
}

function StatusPill({ status }: { status: string }) {
  const config = status === "ACTIVE" ? ["Activa", "bg-emerald-100 text-emerald-800"] : status === "VOID" ? ["Anulada", "bg-rose-100 text-rose-800"] : status === "DRAFT" ? ["Borrador", "bg-amber-100 text-amber-800"] : status === "CLOSED" ? ["Cerrada", "bg-slate-100 text-slate-700"] : status === "ARCHIVED" ? ["Archivada", "bg-slate-100 text-slate-500"] : ["Cancelada", "bg-rose-50 text-rose-700"];
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${config[1]}`}>{config[0]}</span>;
}
function MiniMetric({ label, value }: { label: string; value: string | number }) { return <div><p className="text-lg font-bold text-slate-900">{value}</p><p className="text-[11px] text-slate-500">{label}</p></div>; }
function ImpactStat({ label, value }: { label: string; value: string | number }) { return <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 font-bold">{value}</p></div>; }
function Pagination({ page, total, onPage }: { page: number; total: number; onPage: (page: number) => void }) { const pages = Math.ceil(total / 30); return <div className="flex items-center justify-between rounded-xl border bg-white px-4 py-3 text-sm"><span>Mostrando página {page} de {pages} · {total} registros</span><div className="flex gap-2"><Button disabled={page <= 1} size="sm" variant="secondary" onClick={() => onPage(page - 1)}>Anterior</Button><Button disabled={page >= pages} size="sm" variant="secondary" onClick={() => onPage(page + 1)}>Siguiente</Button></div></div>; }
function EmptyState({ title, description }: { title: string; description: string }) { return <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center"><span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-emerald-50 text-emerald-700"><Leaf className="h-6 w-6" /></span><h2 className="mt-3 font-bold">{title}</h2><p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{description}</p></div>; }
function messageOf(reason: unknown) { return reason instanceof Error ? reason.message : "No se pudo completar la solicitud. Revisa los datos e inténtalo nuevamente."; }
function kg(value: string | number) { return `${kgFormatter.format(Number(value) || 0)} kg`; }
function formatDate(value: string) { return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }
function activationStatusLabel(status: string) { return ({ DRAFT: "Borrador", ACTIVE: "Activa", CLOSED: "Cerrada", CANCELLED: "Cancelada", ARCHIVED: "Archivada" } as Record<string, string>)[status] || status; }
function emailStatus(status: string) { return ({ PENDING: "pendiente", SENT: "enviado", FAILED: "falló", SKIPPED: "sin correo" } as Record<string, string>)[status] || status; }
