"use client";

import { EvidenceUploader } from "@/components/evidences/EvidenceUploader";
import type { Incident } from "@/types/incident";
import type { Task } from "@/types/task";

export function MobileEvidenceForm({
  eventId,
  tasks,
  incidents,
  initialTaskId,
  initialIncidentId,
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
  onSubmit: (formData: FormData) => Promise<void>;
}) {
  return (
    <EvidenceUploader
      eventId={eventId}
      incidents={incidents}
      initialIncidentId={initialIncidentId}
      initialTaskId={initialTaskId}
      loading={loading}
      tasks={tasks}
      onCancel={onCancel}
      onSubmit={onSubmit}
    />
  );
}
