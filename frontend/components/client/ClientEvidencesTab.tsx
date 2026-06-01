"use client";

import { useEffect, useState } from "react";

import { EvidenceGallery } from "@/components/evidences/EvidenceGallery";
import { EvidencePreviewModal } from "@/components/evidences/EvidencePreviewModal";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { getEventEvidences } from "@/lib/api/evidences";
import type { Evidence } from "@/types/evidence";

export function ClientEvidencesTab({ eventId }: { eventId: string }) {
  const [items, setItems] = useState<Evidence[]>([]);
  const [preview, setPreview] = useState<Evidence | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getEventEvidences(eventId);
        setItems(data.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudieron cargar las evidencias.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [eventId]);

  if (loading) return <LoadingState label="Cargando evidencias..." />;
  if (error) return <ErrorState message={error} />;
  return <><EvidenceGallery canDelete={false} evidences={items} onDelete={() => {}} onPreview={setPreview} />{preview ? <EvidencePreviewModal evidence={preview} onClose={() => setPreview(null)} /> : null}</>;
}
