"use client";

import type { Evidence } from "@/types/evidence";
import { EvidenceCard } from "@/components/evidences/EvidenceCard";
import { EmptyState } from "@/components/common/EmptyState";

export function EvidenceGallery({ evidences, canDelete, onPreview, onDelete }: { evidences: Evidence[]; canDelete: boolean; onPreview: (item: Evidence) => void; onDelete: (item: Evidence) => void }) {
  if (evidences.length === 0) return <EmptyState title="Sin evidencias" description="Sube fotos o documentos para respaldar el trabajo realizado." />;
  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{evidences.map((item) => <EvidenceCard key={item.id} canDelete={canDelete} evidence={item} onDelete={onDelete} onPreview={onPreview} />)}</div>;
}
