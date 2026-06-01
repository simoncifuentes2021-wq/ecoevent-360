"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Upload } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { ModalShell } from "@/components/common/ModalShell";
import { EvidenceDeleteDialog } from "@/components/evidences/EvidenceDeleteDialog";
import { EvidenceFilters } from "@/components/evidences/EvidenceFilters";
import { EvidenceGallery } from "@/components/evidences/EvidenceGallery";
import { EvidencePreviewModal } from "@/components/evidences/EvidencePreviewModal";
import { EvidenceUploader } from "@/components/evidences/EvidenceUploader";
import { Button } from "@/components/ui/button";
import { createEvidence, deleteEvidence, getEventEvidences } from "@/lib/api/evidences";
import { getEventIncidents } from "@/lib/api/incidents";
import { getEventTasks } from "@/lib/api/tasks";
import { canDeleteEvidence, canUploadEvidence } from "@/lib/permissions";
import type { Evidence } from "@/types/evidence";
import type { Incident } from "@/types/incident";
import type { UserRole } from "@/types/roles";
import type { Task } from "@/types/task";

export function EvidencesTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [preview, setPreview] = useState<Evidence | null>(null);
  const [deleting, setDeleting] = useState<Evidence | null>(null);
  const [q, setQ] = useState("");
  const [type, setType] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [evidenceData, taskData, incidentData] = await Promise.all([getEventEvidences(eventId), getEventTasks(eventId), getEventIncidents(eventId)]);
      setEvidences(evidenceData.items);
      setTasks(taskData.items);
      setIncidents(incidentData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => evidences.filter((item) => (!q || `${item.description || ""} ${item.filename || ""}`.toLowerCase().includes(q.toLowerCase())) && (!type || (type === "image" ? item.file_type.startsWith("image/") : item.file_type.includes("pdf")))), [evidences, q, type]);

  async function upload(formData: FormData) {
    setSaving(true);
    try {
      await createEvidence(formData);
      setUploadOpen(false);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    await deleteEvidence(deleting.id);
    setDeleting(null);
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div><h2 className="text-xl font-bold text-slate-950">Evidencias</h2><p className="text-sm text-slate-600">Fotos y documentos que respaldan la operacion del evento.</p></div>
        {canUploadEvidence(role) ? <Button onClick={() => setUploadOpen(true)}><Upload className="h-4 w-4" />Subir evidencia</Button> : null}
      </div>
      <EvidenceFilters q={q} type={type} onQChange={setQ} onTypeChange={setType} />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {loading ? <p className="text-sm text-slate-500">Cargando evidencias...</p> : <EvidenceGallery canDelete={canDeleteEvidence(role)} evidences={filtered} onDelete={setDeleting} onPreview={setPreview} />}
      {uploadOpen ? <ModalShell title="Subir evidencia" description="Adjunta imagen o PDF al evento." onClose={() => setUploadOpen(false)}><EvidenceUploader eventId={eventId} incidents={incidents} loading={saving} tasks={tasks} onCancel={() => setUploadOpen(false)} onSubmit={upload} /></ModalShell> : null}
      {preview ? <EvidencePreviewModal evidence={preview} onClose={() => setPreview(null)} /> : null}
      <EvidenceDeleteDialog evidence={deleting} onClose={() => setDeleting(null)} onConfirm={confirmDelete} />
    </div>
  );
}
