"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ExternalLink, FileText, Images, Trash2 } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
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
    <Card>
      <CardContent className="space-y-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-lg font-bold">Evidencias del pedido</h2>
            <p className="text-sm text-muted-foreground">
              Resumen de fotos y documentos subidos en todas las etapas del pedido.
            </p>
          </div>
          <Badge tone={items.length > 0 ? "success" : "neutral"}>{items.length} archivo{items.length === 1 ? "" : "s"}</Badge>
        </div>
        {error ? <ErrorState message={error} onRetry={load} /> : null}
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
                    <a href={url} rel="noreferrer" target="_blank">
                      <Button size="sm" type="button" variant="secondary">
                        <ExternalLink className="h-4 w-4" />
                        Ver
                      </Button>
                    </a>
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
                    <a href={url} rel="noreferrer" target="_blank">
                      <img alt={item.notes || item.file_name || "Evidencia"} className="h-36 w-full rounded-md object-cover" src={url} />
                    </a>
                  ) : (
                    <a className="grid h-36 place-items-center rounded-md bg-slate-100 text-sm font-semibold" href={url} rel="noreferrer" target="_blank">
                      <FileText className="h-7 w-7" />
                      Documento
                    </a>
                  )}
                  {item.notes ? <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{item.notes}</p> : null}
                </div>
              );
            })}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
