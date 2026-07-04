"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Camera, ExternalLink, FileText, Trash2, Upload } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { fileUrl } from "@/lib/files";
import { deleteLogisticsEvidence, getLogisticsEvidences, uploadLogisticsEvidence } from "@/lib/api/logistics-evidences";
import type { LogisticsEvidence, LogisticsEvidenceStage } from "@/types/logistics-evidence";

type EvidenceTarget = {
  logisticsOrderId?: string;
  logisticsOrderItemId?: string;
  purchaseRequestId?: string;
  purchaseRequestItemId?: string | null;
  stockMovementId?: string;
};

export function LogisticsEvidenceUploader({
  logisticsOrderId,
  logisticsOrderItemId,
  purchaseRequestId,
  purchaseRequestItemId,
  stockMovementId,
  stage,
  title,
  required,
  readOnly
}: EvidenceTarget & {
  stage: LogisticsEvidenceStage;
  title: string;
  required?: boolean;
  readOnly?: boolean;
}) {
  const [items, setItems] = useState<LogisticsEvidence[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const target = useMemo(() => {
    if (logisticsOrderItemId) return { logisticsOrderItemId };
    if (purchaseRequestId) return { purchaseRequestId, purchaseRequestItemId };
    if (stockMovementId) return { stockMovementId };
    if (logisticsOrderId) return { logisticsOrderId };
    return null;
  }, [logisticsOrderId, logisticsOrderItemId, purchaseRequestId, purchaseRequestItemId, stockMovementId]);

  const load = useCallback(async () => {
    if (!target) return;
    setLoading(true);
    setError(null);
    try {
      const response = await getLogisticsEvidences(target, { evidence_stage: stage, page: 1, limit: 20 });
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar las evidencias.");
    } finally {
      setLoading(false);
    }
  }, [stage, target]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit() {
    if (!target || !file) return;
    setSaving(true);
    setError(null);
    try {
      await uploadLogisticsEvidence(target, { stage, file, notes: notes || null });
      setFile(null);
      setNotes("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos subir la evidencia.");
    } finally {
      setSaving(false);
    }
  }

  async function removeEvidence(item: LogisticsEvidence) {
    const confirmed = window.confirm("¿Eliminar esta evidencia? Esta accion no se puede deshacer.");
    if (!confirmed) return;
    setDeletingId(item.id);
    setError(null);
    try {
      await deleteLogisticsEvidence(item.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos eliminar la evidencia.");
    } finally {
      setDeletingId(null);
    }
  }

  const status = items.length > 0 ? "Con evidencia" : required ? "Evidencia requerida pendiente" : "Sin evidencia";

  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
          <div>
            <h3 className="font-bold">{title}</h3>
            <p className="text-sm text-muted-foreground">{items.length} evidencia{items.length === 1 ? "" : "s"} registrada{items.length === 1 ? "" : "s"}</p>
          </div>
          <Badge tone={items.length > 0 ? "success" : required ? "warning" : "neutral"}>{status}</Badge>
        </div>
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {!readOnly ? (
          <div className="grid gap-3 rounded-lg border bg-slate-50 p-3">
            <label className="grid gap-2 text-sm font-semibold">
              Foto o documento
              <input
                ref={cameraInputRef}
                accept="image/*"
                capture="environment"
                className="hidden"
                type="file"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
              <input
                ref={fileInputRef}
                accept="image/jpeg,image/png,image/webp,application/pdf"
                className="hidden"
                type="file"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="secondary" onClick={() => cameraInputRef.current?.click()}>
                  <Camera className="h-4 w-4" />
                  Tomar foto
                </Button>
                <Button type="button" variant="secondary" onClick={() => fileInputRef.current?.click()}>
                  <Upload className="h-4 w-4" />
                  Subir archivo
                </Button>
              </div>
            </label>
            <label className="grid gap-2 text-sm font-semibold">
              Nota
              <textarea
                className="min-h-16 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
              />
            </label>
            {file ? <p className="text-xs font-semibold text-emerald-700">{file.name}</p> : null}
            <div>
              <Button disabled={!file || saving} type="button" onClick={submit}>
                {file?.type.startsWith("image/") ? <Camera className="h-4 w-4" /> : <Upload className="h-4 w-4" />}
                {saving ? "Subiendo..." : "Subir evidencia"}
              </Button>
            </div>
          </div>
        ) : null}
        {loading ? <p className="text-sm text-muted-foreground">Cargando evidencias...</p> : null}
        {!loading && items.length === 0 ? <p className="text-sm text-muted-foreground">Aun no hay evidencias en esta etapa.</p> : null}
        {items.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => {
              const url = fileUrl(item.file_url);
              const isImage = item.file_type?.startsWith("image/");
              return (
                <div className="rounded-lg border bg-white p-2 transition hover:border-primary" key={item.id}>
                  <a href={url} rel="noreferrer" target="_blank">
                    {isImage ? (
                      <img alt={item.notes || item.file_name || "Evidencia logistica"} className="h-28 w-full rounded-md object-cover" src={url} />
                    ) : (
                      <div className="grid h-28 place-items-center rounded-md bg-slate-100 text-sm font-semibold">
                        <FileText className="h-6 w-6" />
                        PDF
                      </div>
                    )}
                  </a>
                  <div className="mt-2 flex items-start justify-between gap-2">
                    <a className="min-w-0 flex-1" href={url} rel="noreferrer" target="_blank">
                      <p className="line-clamp-2 text-sm font-semibold">{item.notes || item.file_name || "Evidencia"}</p>
                      <p className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString("es-CL")}</p>
                    </a>
                    <div className="flex shrink-0 gap-1">
                      <a href={url} rel="noreferrer" target="_blank">
                        <Button aria-label="Abrir evidencia" className="h-9 w-9 p-0" size="sm" type="button" variant="ghost">
                          <ExternalLink className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </a>
                      {!readOnly ? (
                        <Button
                          aria-label="Eliminar evidencia"
                          className="h-9 w-9 p-0"
                          disabled={deletingId === item.id}
                          size="sm"
                          type="button"
                          variant="ghost"
                          onClick={() => void removeEvidence(item)}
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
