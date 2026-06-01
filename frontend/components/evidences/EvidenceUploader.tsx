"use client";

import { useState } from "react";

import { FileUploader } from "@/components/files/FileUploader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Evidence } from "@/types/evidence";
import type { FileUpload } from "@/types/file";
import type { Incident } from "@/types/incident";
import type { Task } from "@/types/task";

export function EvidenceUploader({
  eventId,
  tasks,
  incidents,
  initialTaskId = "",
  initialIncidentId = "",
  loading,
  onCancel,
  onSubmit
}: {
  eventId: string;
  tasks: Task[];
  incidents: Incident[];
  initialTaskId?: string;
  initialIncidentId?: string;
  loading?: boolean;
  onCancel: () => void;
  onSubmit: (formData: FormData) => Promise<Evidence | void>;
}) {
  const [file, setFile] = useState<FileUpload | null>(null);
  const [description, setDescription] = useState("");
  const [taskId, setTaskId] = useState(initialTaskId);
  const [incidentId, setIncidentId] = useState(initialIncidentId);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    if (!file) {
      setError("Selecciona un archivo.");
      return;
    }
    const formData = new FormData();
    formData.append("event_id", eventId);
    if (taskId) formData.append("task_id", taskId);
    if (incidentId) formData.append("incident_id", incidentId);
    formData.append("description", description);
    formData.append("file", file.file);
    await onSubmit(formData);
  }

  return (
    <div className="space-y-4">
      {error ? <p className="rounded-2xl bg-rose-50 p-3 text-sm font-semibold text-rose-700">{error}</p> : null}
      <FileUploader value={file} onChange={setFile} />
      <label className="grid gap-2 text-sm font-semibold">Descripcion<Input value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="grid gap-2 text-sm font-semibold">Tarea<select className="h-12 rounded-2xl border px-4" value={taskId} onChange={(event) => setTaskId(event.target.value)}><option value="">Sin tarea</option>{tasks.map((task) => <option key={task.id} value={task.id}>{task.title}</option>)}</select></label>
        <label className="grid gap-2 text-sm font-semibold">Incidencia<select className="h-12 rounded-2xl border px-4" value={incidentId} onChange={(event) => setIncidentId(event.target.value)}><option value="">Sin incidencia</option>{incidents.map((incident) => <option key={incident.id} value={incident.id}>{incident.title}</option>)}</select></label>
      </div>
      <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button><Button disabled={loading} type="button" onClick={submit}>{loading ? "Subiendo..." : "Subir evidencia"}</Button></div>
    </div>
  );
}
