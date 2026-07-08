"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, Eye, FileText, Images, Trash2 } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LogisticsEvidencePreviewModal } from "@/components/logistics/LogisticsEvidencePreviewModal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { fileUrl } from "@/lib/files";
import { deleteLogisticsEvidence, getLogisticsEvidences } from "@/lib/api/logistics-evidences";
import type { LogisticsEvidence, LogisticsEvidenceStage } from "@/types/logistics-evidence";

const stageLabels: Record<LogisticsEvidenceStage, string> = {
  LOGISTICS_PREPARATION: "Preparacion",
  LOGISTICS_LOADING: "Carga",
  LOGISTICS_DISPATCH: "Salida de bodega",
  LOGISTICS_DELIVERY: "Entrega en terreno",
  LOGISTICS_OUTCOME: "Resultado",
  LOGISTICS_RETURN: "Retorno usable",
  LOGISTICS_DAMAGED_RETURN: "Retorno danado",
  LOGISTICS_LOSS: "Perdida",
  LOGISTICS_DISCARDED: "Descartado",
  LOGISTICS_CLOSURE: "Cierre",
  PURCHASE_REQUEST: "Solicitud de compra",
  PURCHASE_RECEIPT: "Compra recibida",
  PURCHASE_WAREHOUSE_RECEIPT: "Recepcion en bodega",
  PURCHASE_DIRECT_EVENT_DELIVERY: "Entrega directa",
  STOCK_ADJUSTMENT: "Ajuste de stock",
  STOCK_DAMAGE: "Dano de stock",
  STOCK_LOSS: "Perdida de stock",
  STOCK_CORRECTION: "Correccion de stock"
};

export function LogisticsEvidenceGallery({
  logisticsOrderId,
  orderItems
}: {
  logisticsOrderId: string;
  orderItems: Array<{ id: string; item_name_snapshot: string }>;
}) {
  const [items, setItems] = useState<LogisticsEvidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [preview, setPreview] = useState<LogisticsEvidence | null>(null);
  const itemNames = useMemo(
    () => new Map(orderItems.map((item) => [item.id, item.item_name_snapshot])),
    [orderItems]
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getLogisticsEvidences(
        { logisticsOrderId },
        { include_items: true, page: 1, limit: 100 }
      );
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar las evidencias del pedido.");
    } finally {
      setLoading(false);
    }
  }, [logisticsOrderId]);

  useEffect(() => {
    void load();
  }, [load]);

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

  return (
    <Card className="overflow-hidden border-slate-200 bg-white/95 shadow-[0_8px_24px_rgba(15,23,42,0.06)]">
      <CardContent className="space-y-3 p-0">
        <div className="grid grid-cols-[1fr_auto] items-start gap-3 px-3.5 pt-3.5 sm:px-4 sm:pt-4">
          <button className="min-w-0 flex-1 text-left" type="button" onClick={() => setExpanded((current) => !current)}>
            <h2 className="text-base font-bold leading-snug text-slate-900 sm:text-lg">Evidencias del pedido</h2>
            <p className="text-sm text-muted-foreground">
              Resumen de fotos y documentos subidos en todas las etapas del pedido.
            </p>
          </button>
          <div className="flex shrink-0 items-center justify-end gap-1.5">
            <Badge tone={items.length > 0 ? "success" : "neutral"}>{items.length} archivo{items.length === 1 ? "" : "s"}</Badge>
            <Button
              aria-label={expanded ? "Ocultar evidencias del pedido" : "Mostrar evidencias del pedido"}
              className="h-8 w-8 rounded-full p-0"
              type="button"
              variant="ghost"
              onClick={() => setExpanded((current) => !current)}
            >
              <ChevronDown className={`h-4 w-4 transition ${expanded ? "rotate-180" : ""}`} />
            </Button>
          </div>
        </div>
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {expanded ? (
          <div className="space-y-3 px-3.5 pb-3.5 sm:px-4 sm:pb-4">
            {loading ? <p className="text-sm text-muted-foreground">Cargando evidencias...</p> : null}
            {!loading && !error && items.length === 0 ? (
              <EmptyState
                icon={<Images className="h-6 w-6" />}
                title="Sin evidencias registradas"
                description="Cuando se suban fotos o documentos en preparacion, salida, entrega o resultados apareceran aqui."
              />
            ) : null}
            {items.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {items.map((item) => {
                  const url = fileUrl(item.file_url);
                  const isImage = item.file_type?.startsWith("image/");
                  const source = item.logistics_order_item_id
                    ? itemNames.get(item.logistics_order_item_id) || "Producto del pedido"
                    : "Pedido";
                  return (
                    <div className="rounded-lg border bg-white p-3" key={item.id}>
                      <div className="mb-3 flex items-start justify-between gap-2">
                        <div>
                          <Badge tone="neutral">{stageLabels[item.evidence_stage]}</Badge>
                          <p className="mt-2 text-sm font-semibold">{source}</p>
                          <p className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString("es-CL")}</p>
                        </div>
                        <Button size="sm" type="button" variant="secondary" onClick={() => setPreview(item)}>
                          <Eye className="h-4 w-4" />
                          Ver
                        </Button>
                        <Button
                          aria-label="Eliminar evidencia"
                          disabled={deletingId === item.id}
                          size="sm"
                          type="button"
                          variant="ghost"
                          onClick={() => void removeEvidence(item)}
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      </div>
                      {isImage ? (
                        <button className="block w-full" type="button" onClick={() => setPreview(item)}>
                          <img alt={item.notes || item.file_name || "Evidencia"} className="h-36 w-full rounded-md object-cover" src={url} />
                        </button>
                      ) : (
                        <button className="grid h-36 w-full place-items-center rounded-md bg-slate-100 text-sm font-semibold" type="button" onClick={() => setPreview(item)}>
                          <FileText className="h-7 w-7" />
                          Documento
                        </button>
                      )}
                      {item.notes ? <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{item.notes}</p> : null}
                    </div>
                  );
                })}
              </div>
            ) : null}
          </div>
        ) : (
          <div className="mx-3.5 mb-3.5 flex items-center justify-between gap-3 rounded-md bg-slate-50/90 px-3 py-2.5 text-sm text-muted-foreground sm:mx-4 sm:mb-4">
            <span className="min-w-0 leading-snug">{items.length > 0 ? "Toca para revisar los archivos." : "Sin evidencias registradas."}</span>
            <Button className="shrink-0 shadow-sm" size="sm" type="button" variant="secondary" onClick={() => setExpanded(true)}>
              Ver
            </Button>
          </div>
        )}
        {preview ? <LogisticsEvidencePreviewModal evidence={preview} onClose={() => setPreview(null)} /> : null}
      </CardContent>
    </Card>
  );
}
