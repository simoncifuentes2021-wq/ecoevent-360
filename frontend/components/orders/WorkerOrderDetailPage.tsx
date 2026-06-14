"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Camera, CheckCircle2 } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { CameraFilePicker } from "@/components/files/CameraFilePicker";
import { MobileShell } from "@/components/worker/MobileShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getOrder, getOrderEvidences, markOrderItemStage, uploadOrderEvidence } from "@/lib/api/orders";
import type { EventOrder, EventOrderItem, OrderEvidence, OrderEvidenceStage } from "@/types/order";
import { dateValue, ItemStageBadge, numberValue, OrderStatusBadge, ProgressLine, stageLabels } from "@/components/orders/order-ui";

export function WorkerOrderDetailPage({ orderId }: { orderId: string }) {
  const [order, setOrder] = useState<EventOrder | null>(null);
  const [evidences, setEvidences] = useState<OrderEvidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ item: EventOrderItem; stage: OrderEvidenceStage } | null>(null);
  const [upload, setUpload] = useState<{ item: EventOrderItem; stage: OrderEvidenceStage } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [orderData, evidenceData] = await Promise.all([getOrder(orderId), getOrderEvidences(orderId)]);
      setOrder(orderData);
      setEvidences(evidenceData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el pedido.");
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => { void load(); }, [load]);

  async function mark(item: EventOrderItem, stage: OrderEvidenceStage, observation?: string | null) {
    await markOrderItemStage(item.id, stage, "COMPLETED", observation);
    setConfirm(null);
    await load();
  }

  async function uploadFile(item: EventOrderItem, stage: OrderEvidenceStage, file: File, description?: string | null) {
    await uploadOrderEvidence(orderId, { file, stage, order_item_id: item.id, description });
    setUpload(null);
    await load();
  }

  if (loading) return <LoadingState label="Cargando pedido..." />;
  if (error || !order) return <ErrorState message={error || "Pedido no encontrado"} onRetry={load} />;

  return (
    <MobileShell title={order.title} description={`${order.event?.name || "Evento"} · ${order.event?.client?.business_name || "Cliente"}`}>
      <Link href="/worker/pedidos"><Button className="w-full" variant="secondary"><ArrowLeft className="h-4 w-4" />Volver a mis pedidos</Button></Link>
      <Card><CardContent className="space-y-3 p-4"><div className="flex items-center justify-between gap-3"><OrderStatusBadge status={order.status} /><p className="text-sm font-semibold">Requerido: {dateValue(order.required_date)}</p></div><ProgressLine label="Carga" value={order.progress.load_progress_percentage} count={`${order.progress.loaded_items}/${order.progress.total_items}`} /><ProgressLine label="Entrega" value={order.progress.delivery_progress_percentage} count={`${order.progress.delivered_items}/${order.progress.total_items}`} /><ProgressLine label="Retorno" value={order.progress.return_progress_percentage} count={`${order.progress.returned_items}/${order.progress.total_items}`} /></CardContent></Card>
      <WorkerEvidenceSummary evidences={evidences} />
      <div className="grid gap-4">
        {(order.items || []).map((item) => (
          <Card key={item.id}>
            <CardContent className="space-y-4 p-4">
              <div><p className="text-lg font-bold">{item.item_name_snapshot}</p><p className="text-sm text-slate-600">{numberValue(item.quantity)} {item.unit || ""}</p></div>
              <WorkerStage evidences={evidencesFor(evidences, item.id, "LOAD")} label="Carga" status={item.load_status} onMark={() => setConfirm({ item, stage: "LOAD" })} onUpload={() => setUpload({ item, stage: "LOAD" })} />
              <WorkerStage evidences={evidencesFor(evidences, item.id, "DELIVERY")} label="Entrega" status={item.delivery_status} onMark={() => setConfirm({ item, stage: "DELIVERY" })} onUpload={() => setUpload({ item, stage: "DELIVERY" })} />
              <WorkerStage evidences={evidencesFor(evidences, item.id, "RETURN")} label="Retorno" status={item.return_status} onMark={() => setConfirm({ item, stage: "RETURN" })} onUpload={() => setUpload({ item, stage: "RETURN" })} />
            </CardContent>
          </Card>
        ))}
      </div>
      {confirm ? <ConfirmStageModal target={confirm} onClose={() => setConfirm(null)} onConfirm={mark} /> : null}
      {upload ? <UploadStageModal target={upload} onClose={() => setUpload(null)} onConfirm={uploadFile} /> : null}
    </MobileShell>
  );
}

function WorkerEvidenceSummary({ evidences }: { evidences: OrderEvidence[] }) {
  const load = evidences.filter((evidence) => evidence.stage === "LOAD");
  const delivery = evidences.filter((evidence) => evidence.stage === "DELIVERY");
  const returned = evidences.filter((evidence) => evidence.stage === "RETURN");

  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <div>
          <p className="text-base font-bold text-slate-950">Evidencias subidas</p>
          <p className="text-xs text-slate-500">Revisa aquí las fotos ya cargadas para no repetirlas.</p>
        </div>
        <EvidenceGroup label="Carga" evidences={load} />
        <EvidenceGroup label="Entrega" evidences={delivery} />
        <EvidenceGroup label="Retorno" evidences={returned} />
      </CardContent>
    </Card>
  );
}

function EvidenceGroup({ label, evidences }: { label: string; evidences: OrderEvidence[] }) {
  return (
    <div className="rounded-lg border bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-bold">{label}</p>
        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-slate-600">{evidences.length}</span>
      </div>
      <EvidenceStrip evidences={evidences} compact />
    </div>
  );
}

function evidencesFor(evidences: OrderEvidence[], itemId: string, stage: OrderEvidenceStage) {
  return evidences.filter((evidence) => evidence.order_item_id === itemId && evidence.stage === stage);
}

function WorkerStage({ label, status, evidences, onMark, onUpload }: { label: string; status: EventOrderItem["load_status"]; evidences: OrderEvidence[]; onMark: () => void; onUpload: () => void }) {
  return (
    <div className="rounded-lg border bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-bold">{label}</p>
        <ItemStageBadge status={status} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Button className="h-12" onClick={onMark}><CheckCircle2 className="h-4 w-4" />Marcar</Button>
        <Button className="h-12" variant="secondary" onClick={onUpload}><Camera className="h-4 w-4" />Foto</Button>
      </div>
      <EvidenceStrip evidences={evidences} />
    </div>
  );
}

function EvidenceStrip({ evidences, compact = false }: { evidences: OrderEvidence[]; compact?: boolean }) {
  if (evidences.length === 0) {
    return <p className="mt-3 rounded-md border border-dashed border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-500">Sin fotos subidas en esta etapa.</p>;
  }

  return (
    <div className="mt-3 space-y-2">
      {!compact ? <p className="text-xs font-bold text-emerald-700">{evidences.length} evidencia{evidences.length === 1 ? "" : "s"} subida{evidences.length === 1 ? "" : "s"}</p> : null}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {evidences.map((evidence) => (
          <a className="block shrink-0" href={evidence.file_url} key={evidence.id} rel="noreferrer" target="_blank">
            {evidence.file_type?.startsWith("image/") ? (
              <img alt={evidence.description || "Evidencia subida"} className="h-20 w-20 rounded-md border object-cover" src={evidence.file_url} />
            ) : (
              <div className="grid h-20 w-20 place-items-center rounded-md border bg-white text-xs font-bold text-slate-600">PDF</div>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}

function ConfirmStageModal({ target, onClose, onConfirm }: { target: { item: EventOrderItem; stage: OrderEvidenceStage }; onClose: () => void; onConfirm: (item: EventOrderItem, stage: OrderEvidenceStage, observation?: string | null) => Promise<void> }) {
  const [observation, setObservation] = useState("");
  const [saving, setSaving] = useState(false);
  async function submit() {
    setSaving(true);
    try { await onConfirm(target.item, target.stage, observation); } finally { setSaving(false); }
  }
  return <ModalShell title={`Marcar ${stageLabels[target.stage].toLowerCase()}`} description={target.item.item_name_snapshot} onClose={onClose}><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}><label className="grid gap-2 text-sm font-semibold">Observación opcional<Input value={observation} onChange={(event) => setObservation(event.target.value)} /></label><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={saving} type="submit">{saving ? "Guardando..." : "Confirmar"}</Button></div></form></ModalShell>;
}

function UploadStageModal({ target, onClose, onConfirm }: { target: { item: EventOrderItem; stage: OrderEvidenceStage }; onClose: () => void; onConfirm: (item: EventOrderItem, stage: OrderEvidenceStage, file: File, description?: string | null) => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  async function submit() {
    if (!file) return;
    setSaving(true);
    try { await onConfirm(target.item, target.stage, file, description); } finally { setSaving(false); }
  }
  return <ModalShell title={`Subir foto de ${stageLabels[target.stage].toLowerCase()}`} description={target.item.item_name_snapshot} onClose={onClose}><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}><div className="space-y-2"><CameraFilePicker onFile={setFile} />{file ? <p className="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800">Lista para subir: {file.name}</p> : null}</div><label className="grid gap-2 text-sm font-semibold">Descripción<Input value={description} onChange={(event) => setDescription(event.target.value)} /></label><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={!file || saving} type="submit">{saving ? "Subiendo..." : "Subir"}</Button></div></form></ModalShell>;
}
