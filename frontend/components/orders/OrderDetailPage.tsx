"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Camera, CheckCircle2, PackagePlus, Pencil, Trash2 } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { CameraFilePicker } from "@/components/files/CameraFilePicker";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getCatalogItems } from "@/lib/api/orders";
import { createOrderItem, deleteOrderEvidence, deleteOrderItem, getOrder, getOrderEvidences, markOrderItemStage, updateOrder, uploadOrderEvidence } from "@/lib/api/orders";
import { getEventStaff } from "@/lib/api/staff";
import { getEventZones } from "@/lib/api/zones";
import type { CatalogItem, EventOrder, EventOrderItem, EventOrderItemCreate, EventOrderUpdate, OrderEvidence, OrderEvidenceStage } from "@/types/order";
import type { EventStaff } from "@/types/staff";
import type { Zone } from "@/types/zone";
import { dateValue, ItemStageBadge, money, numberValue, OrderStatusBadge, ProgressLine, stageLabels } from "@/components/orders/order-ui";

const stages: OrderEvidenceStage[] = ["LOAD", "DELIVERY", "RETURN"];
type ItemFormState = Omit<EventOrderItemCreate, "quantity"> & { quantity: string };

export function OrderDetailPage({ orderId, readOnly = false, backHref = "/admin/eventos" }: { orderId: string; readOnly?: boolean; backHref?: string }) {
  const [order, setOrder] = useState<EventOrder | null>(null);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [staff, setStaff] = useState<EventStaff[]>([]);
  const [evidences, setEvidences] = useState<OrderEvidence[]>([]);
  const [active, setActive] = useState<"resumen" | "items" | "logistica" | "evidencias">("resumen");
  const [stage, setStage] = useState<OrderEvidenceStage>("LOAD");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [itemFormOpen, setItemFormOpen] = useState(false);
  const [editFormOpen, setEditFormOpen] = useState(false);
  const [markingKey, setMarkingKey] = useState<string | null>(null);
  const [evidenceTarget, setEvidenceTarget] = useState<{ item?: EventOrderItem; stage: OrderEvidenceStage } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const orderData = await getOrder(orderId);
      setOrder(orderData);
      const [catalogData, zoneData, evidenceData, staffData] = await Promise.all([
        readOnly ? Promise.resolve({ items: [] }) : getCatalogItems({ is_active: "true", page: 1, limit: 100 }),
        readOnly ? Promise.resolve([]) : getEventZones(orderData.event_id),
        getOrderEvidences(orderId),
        readOnly ? Promise.resolve([]) : getEventStaff(orderData.event_id)
      ]);
      setCatalog(catalogData.items);
      setZones(zoneData);
      setEvidences(evidenceData);
      setStaff(staffData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el pedido.");
    } finally {
      setLoading(false);
    }
  }, [orderId, readOnly]);

  useEffect(() => { void load(); }, [load]);

  const evidencesByStage = useMemo(() => evidences.filter((item) => item.stage === stage), [evidences, stage]);
  const assignees = useMemo(() => staff.filter((item) => item.user && ["WORKER", "SUPERVISOR"].includes(item.user.role)), [staff]);

  if (loading) return <LoadingState label="Cargando pedido..." />;
  if (error || !order) return <ErrorState message={error || "Pedido no encontrado"} title="No pudimos cargar el pedido" onRetry={load} />;

  async function addItem(data: EventOrderItemCreate) {
    if (!order) return;
    await createOrderItem(order.id, data);
    setItemFormOpen(false);
    await load();
  }

  async function removeItem(item: EventOrderItem) {
    if (!order) return;
    await deleteOrderItem(order.id, item.id);
    await load();
  }

  async function mark(item: EventOrderItem, itemStage: OrderEvidenceStage) {
    const key = stageKey(item.id, itemStage);
    setMarkingKey(key);
    try {
      const updatedItem = await markOrderItemStage(item.id, itemStage, "COMPLETED");
      setOrder((current) => updateOrderItemLocally(current, updatedItem));
    } finally {
      setMarkingKey(null);
    }
  }

  async function removeEvidence(evidence: OrderEvidence) {
    await deleteOrderEvidence(evidence.id);
    await load();
  }

  async function saveOrder(data: EventOrderUpdate) {
    if (!order) return;
    await updateOrder(order.id, data);
    setEditFormOpen(false);
    await load();
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={order.title}
        description={`${order.event?.name || "Evento"} · ${order.event?.client?.business_name || "Cliente"}`}
        actions={
          <div className="flex flex-wrap gap-2">
            {!readOnly ? (
              <Button onClick={() => setEditFormOpen(true)} type="button">
                <Pencil className="h-4 w-4" />
                Editar pedido
              </Button>
            ) : null}
            <Link href={backHref}>
              <Button variant="secondary"><ArrowLeft className="h-4 w-4" />Volver</Button>
            </Link>
          </div>
        }
      />
      <Card>
        <CardContent className="grid gap-4 p-5 lg:grid-cols-[1.2fr_1fr]">
          <div className="space-y-2">
            <OrderStatusBadge status={order.status} />
            <p className="text-sm text-slate-600">Encargado: {order.assignee?.full_name || "Sin asignar"}</p>
            <p className="text-sm text-slate-600">Fecha requerida: {dateValue(order.required_date)}</p>
            {!readOnly ? <p className="text-lg font-bold">{money(order.total_amount)}</p> : null}
          </div>
          <div className="grid gap-2">
            <ProgressLine label="Carga" value={order.progress.load_progress_percentage} count={`${order.progress.loaded_items}/${order.progress.total_items}`} />
            <ProgressLine label="Entrega" value={order.progress.delivery_progress_percentage} count={`${order.progress.delivered_items}/${order.progress.total_items}`} />
            <ProgressLine label="Retorno" value={order.progress.return_progress_percentage} count={`${order.progress.returned_items}/${order.progress.total_items}`} />
          </div>
        </CardContent>
      </Card>
      <div className="overflow-x-auto rounded-lg border bg-white p-2">
        <div className="flex min-w-max gap-2">
          {(["resumen", "items", "logistica", "evidencias"] as const).map((tab) => (
            <button className={`rounded-md px-3 py-2 text-sm font-semibold ${active === tab ? "bg-emerald-700 text-white" : "text-slate-600 hover:bg-slate-100"}`} key={tab} onClick={() => setActive(tab)} type="button">
              {tab === "items" ? "Ítems" : tab === "logistica" ? "Logística" : tab === "evidencias" ? "Evidencias" : "Resumen"}
            </button>
          ))}
        </div>
      </div>
      {active === "resumen" ? <Summary order={order} readOnly={readOnly} /> : null}
      {active === "items" ? <ItemsSection order={order} readOnly={readOnly} onAdd={() => setItemFormOpen(true)} onRemove={removeItem} /> : null}
      {active === "logistica" ? <LogisticsSection markingKey={markingKey} order={order} readOnly={readOnly} onMark={mark} onUpload={(item, itemStage) => setEvidenceTarget({ item, stage: itemStage })} /> : null}
      {active === "evidencias" ? <EvidencesSection evidences={evidencesByStage} readOnly={readOnly} stage={stage} onDelete={removeEvidence} onStageChange={setStage} /> : null}
      {editFormOpen ? <EditOrderForm assignees={assignees} order={order} onClose={() => setEditFormOpen(false)} onSubmit={saveOrder} /> : null}
      {itemFormOpen ? <ItemForm catalog={catalog} zones={zones} onClose={() => setItemFormOpen(false)} onSubmit={addItem} /> : null}
      {evidenceTarget ? <EvidenceForm orderId={order.id} target={evidenceTarget} onClose={() => setEvidenceTarget(null)} onSaved={load} /> : null}
    </div>
  );
}

function Summary({ order, readOnly }: { order: EventOrder; readOnly: boolean }) {
  return (
    <Card><CardContent className="grid gap-4 p-5 md:grid-cols-2">
      <Info label="Descripción" value={order.description || "Sin descripción"} />
      <Info label="Notas" value={readOnly ? "No disponible" : order.notes || "Sin notas"} />
      <Info label="Ítems" value={`${order.progress.total_items}`} />
      <Info label="Creado" value={dateValue(order.created_at)} />
    </CardContent></Card>
  );
}

function ItemsSection({ order, readOnly, onAdd, onRemove }: { order: EventOrder; readOnly: boolean; onAdd: () => void; onRemove: (item: EventOrderItem) => Promise<void> }) {
  return (
    <Card><CardContent className="space-y-4 p-5">
      {!readOnly ? <div className="flex justify-end"><Button onClick={onAdd}><PackagePlus className="h-4 w-4" />Agregar ítem</Button></div> : null}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b text-xs uppercase text-slate-500"><tr><th className="py-3">Elemento</th><th>Cantidad</th><th>Unidad</th>{!readOnly ? <th>Precio</th> : null}{!readOnly ? <th>Total</th> : null}<th className="text-right">Acciones</th></tr></thead>
          <tbody>{(order.items || []).map((item) => <tr className="border-b last:border-0" key={item.id}><td className="py-3 font-semibold">{item.item_name_snapshot}</td><td>{numberValue(item.quantity)}</td><td>{item.unit || "-"}</td>{!readOnly ? <td>{money(item.unit_price)}</td> : null}{!readOnly ? <td>{money(item.total_price)}</td> : null}<td className="text-right">{!readOnly ? <Button size="sm" variant="secondary" onClick={() => onRemove(item)}><Trash2 className="h-4 w-4" />Quitar</Button> : null}</td></tr>)}</tbody>
        </table>
      </div>
    </CardContent></Card>
  );
}

function LogisticsSection({ markingKey, order, readOnly, onMark, onUpload }: { markingKey: string | null; order: EventOrder; readOnly: boolean; onMark: (item: EventOrderItem, stage: OrderEvidenceStage) => Promise<void>; onUpload: (item: EventOrderItem, stage: OrderEvidenceStage) => void }) {
  return (
    <div className="grid gap-3">
      {(order.items || []).map((item) => (
        <Card key={item.id}><CardContent className="grid gap-4 p-5 lg:grid-cols-[1fr_1.4fr]">
          <div><p className="font-bold">{item.item_name_snapshot}</p><p className="text-sm text-slate-600">{numberValue(item.quantity)} {item.unit || ""}</p></div>
          <div className="grid gap-3 md:grid-cols-3">
            <StageBox isMarking={markingKey === stageKey(item.id, "LOAD")} label="Carga" status={item.load_status} date={item.loaded_at} readOnly={readOnly} onMark={() => onMark(item, "LOAD")} onUpload={() => onUpload(item, "LOAD")} />
            <StageBox isMarking={markingKey === stageKey(item.id, "DELIVERY")} label="Entrega" status={item.delivery_status} date={item.delivered_at} readOnly={readOnly} onMark={() => onMark(item, "DELIVERY")} onUpload={() => onUpload(item, "DELIVERY")} />
            <StageBox isMarking={markingKey === stageKey(item.id, "RETURN")} label="Retorno" status={item.return_status} date={item.returned_at} readOnly={readOnly} onMark={() => onMark(item, "RETURN")} onUpload={() => onUpload(item, "RETURN")} />
          </div>
        </CardContent></Card>
      ))}
    </div>
  );
}

function StageBox({ isMarking, label, status, date, readOnly, onMark, onUpload }: { isMarking: boolean; label: string; status: EventOrderItem["load_status"]; date?: string | null; readOnly: boolean; onMark: () => void; onUpload: () => void }) {
  return <div className="rounded-lg border bg-slate-50 p-3"><p className="text-xs font-bold uppercase text-slate-500">{label}</p><div className="mt-2"><ItemStageBadge status={status} /></div><p className="mt-2 text-xs text-slate-500">{dateValue(date)}</p>{!readOnly ? <div className="mt-3 grid gap-2"><Button disabled={isMarking || status === "COMPLETED"} size="sm" onClick={onMark}><CheckCircle2 className="h-4 w-4" />{isMarking ? "Marcando..." : status === "COMPLETED" ? "Marcado" : "Marcar"}</Button><Button size="sm" variant="secondary" onClick={onUpload}><Camera className="h-4 w-4" />Subir foto</Button></div> : null}</div>;
}

function EvidencesSection({ evidences, stage, readOnly, onStageChange, onDelete }: { evidences: OrderEvidence[]; stage: OrderEvidenceStage; readOnly: boolean; onStageChange: (stage: OrderEvidenceStage) => void; onDelete: (evidence: OrderEvidence) => Promise<void> }) {
  return (
    <Card><CardContent className="space-y-4 p-5">
      <div className="flex gap-2">{stages.map((item) => <Button key={item} variant={stage === item ? "primary" : "secondary"} onClick={() => onStageChange(item)}>{stageLabels[item]}</Button>)}</div>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {evidences.map((evidence) => <div className="rounded-lg border p-3" key={evidence.id}>{evidence.file_type?.startsWith("image/") ? <img alt={evidence.description || "Evidencia"} className="h-40 w-full rounded-md object-cover" src={evidence.file_url} /> : <div className="grid h-40 place-items-center rounded-md bg-slate-100 text-sm font-semibold">PDF</div>}<p className="mt-2 text-sm font-semibold">{evidence.description || "Sin descripción"}</p><p className="text-xs text-slate-500">{dateValue(evidence.created_at)}</p>{!readOnly ? <Button className="mt-3 w-full" size="sm" variant="secondary" onClick={() => onDelete(evidence)}>Eliminar</Button> : null}</div>)}
      </div>
      {evidences.length === 0 ? <p className="text-sm text-slate-500">No hay evidencias en esta etapa.</p> : null}
    </CardContent></Card>
  );
}

function EditOrderForm({ assignees, order, onClose, onSubmit }: { assignees: EventStaff[]; order: EventOrder; onClose: () => void; onSubmit: (data: EventOrderUpdate) => Promise<void> }) {
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<EventOrderUpdate>({
    title: order.title,
    description: order.description || "",
    assigned_to: order.assigned_to || "",
    required_date: toDateTimeLocal(order.required_date),
    notes: order.notes || ""
  });
  const valid = Boolean(form.title?.trim());

  async function submit() {
    setSaving(true);
    try {
      await onSubmit({
        title: form.title,
        description: form.description || null,
        assigned_to: form.assigned_to || null,
        required_date: form.required_date || null,
        notes: form.notes || null
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Editar pedido" description="Puedes dejarlo sin encargado y asignarlo despues." onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); if (valid) void submit(); }}>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Titulo
            <Input value={form.title || ""} onChange={(event) => setForm({ ...form, title: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Fecha requerida
            <Input type="datetime-local" value={form.required_date || ""} onChange={(event) => setForm({ ...form, required_date: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Encargado
            <select className="h-10 rounded-md border border-slate-200 px-3 text-sm" value={form.assigned_to || ""} onChange={(event) => setForm({ ...form, assigned_to: event.target.value })}>
              <option value="">Sin asignar</option>
              {assignees.map((item) => (
                <option key={item.user_id} value={item.user_id}>
                  {item.user?.full_name} - {item.user?.role}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Notas
            <Input value={form.notes || ""} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          </label>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Descripcion
          <Input value={form.description || ""} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        </label>
        {assignees.length === 0 ? <p className="rounded-lg bg-amber-50 p-3 text-sm font-semibold text-amber-800">No hay trabajadores o supervisores asignados al evento todavia.</p> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Guardar cambios"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function ItemForm({ catalog, zones, onClose, onSubmit }: { catalog: CatalogItem[]; zones: Zone[]; onClose: () => void; onSubmit: (data: EventOrderItemCreate) => Promise<void> }) {
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<ItemFormState>({ catalog_item_id: "", item_name_snapshot: "", quantity: "1", unit_price: 0, unit: "", zone_id: "", notes: "" });
  const selected = catalog.find((item) => item.id === form.catalog_item_id);
  const valid = Number(form.quantity || 0) > 0 && Boolean(form.catalog_item_id || form.item_name_snapshot);

  async function submit() {
    setSaving(true);
    try {
      await onSubmit({
        ...form,
        quantity: Number(form.quantity || 0),
        catalog_item_id: form.catalog_item_id || null,
        item_name_snapshot: form.item_name_snapshot || null,
        zone_id: form.zone_id || null,
        unit: form.unit || selected?.unit || null,
        unit_price: form.unit_price ?? Number(selected?.default_unit_price || 0),
        notes: form.notes || null
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Agregar item" onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); if (valid) void submit(); }}>
        <label className="grid gap-2 text-sm font-semibold">
          Catalogo
          <select
            className="h-10 rounded-md border px-3"
            value={form.catalog_item_id || ""}
            onChange={(event) => {
              const item = catalog.find((catalogItem) => catalogItem.id === event.target.value);
              setForm({ ...form, catalog_item_id: event.target.value, item_name_snapshot: item?.name || "", unit: item?.unit || "", unit_price: Number(item?.default_unit_price || 0) });
            }}
          >
            <option value="">Elemento manual</option>
            {catalog.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Nombre
          <Input value={form.item_name_snapshot || ""} onChange={(event) => setForm({ ...form, item_name_snapshot: event.target.value })} />
        </label>
        <div className="grid gap-3 md:grid-cols-3">
          <label className="grid gap-2 text-sm font-semibold">
            Cantidad
            <Input min={0.01} step="0.01" type="number" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: cleanQuantityInput(event.target.value) })} onFocus={(event) => event.currentTarget.select()} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Unidad
            <Input value={form.unit || ""} onChange={(event) => setForm({ ...form, unit: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Precio
            <Input min={0} type="number" value={form.unit_price || 0} onChange={(event) => setForm({ ...form, unit_price: Number(event.target.value) })} />
          </label>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Zona
          <select className="h-10 rounded-md border px-3" value={form.zone_id || ""} onChange={(event) => setForm({ ...form, zone_id: event.target.value })}>
            <option value="">Sin zona</option>
            {zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}
          </select>
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Notas
          <Input value={form.notes || ""} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
        </label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Agregar"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function EvidenceForm({ orderId, target, onClose, onSaved }: { orderId: string; target: { item?: EventOrderItem; stage: OrderEvidenceStage }; onClose: () => void; onSaved: () => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  async function submit() {
    if (!file) return;
    setSaving(true);
    try {
      await uploadOrderEvidence(orderId, { file, stage: target.stage, order_item_id: target.item?.id, description });
      onClose();
      await onSaved();
    } finally {
      setSaving(false);
    }
  }
  return <ModalShell title={`Subir foto de ${stageLabels[target.stage].toLowerCase()}`} description={target.item?.item_name_snapshot} onClose={onClose}><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}><div className="space-y-2"><CameraFilePicker onFile={setFile} />{file ? <p className="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800">Lista para subir: {file.name}</p> : null}</div><label className="grid gap-2 text-sm font-semibold">Descripción<Input value={description} onChange={(event) => setDescription(event.target.value)} /></label><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={!file || saving} type="submit">{saving ? "Subiendo..." : "Subir"}</Button></div></form></ModalShell>;
}

function Info({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border bg-slate-50 p-4"><p className="text-xs font-bold uppercase text-slate-500">{label}</p><p className="mt-2 text-sm font-semibold text-slate-800">{value}</p></div>;
}

function toDateTimeLocal(value?: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function cleanQuantityInput(value: string) {
  if (!value) return "";
  if (value.includes(".")) {
    const [whole, decimal] = value.split(".", 2);
    return `${whole.replace(/^0+(?=\d)/, "") || "0"}.${decimal}`;
  }
  return value.replace(/^0+(?=\d)/, "");
}

function stageKey(itemId: string, stage: OrderEvidenceStage) {
  return `${itemId}:${stage}`;
}

function updateOrderItemLocally(order: EventOrder | null, updatedItem: EventOrderItem) {
  if (!order) return order;
  const items = (order.items || []).map((item) => (item.id === updatedItem.id ? updatedItem : item));
  return {
    ...order,
    items,
    progress: buildOrderProgress(items)
  };
}

function buildOrderProgress(items: EventOrderItem[]) {
  const total = items.length;
  const loaded = items.filter((item) => item.load_status === "COMPLETED").length;
  const delivered = items.filter((item) => item.delivery_status === "COMPLETED").length;
  const returned = items.filter((item) => item.return_status === "COMPLETED").length;
  return {
    total_items: total,
    loaded_items: loaded,
    delivered_items: delivered,
    returned_items: returned,
    load_progress_percentage: progressPercent(loaded, total),
    delivery_progress_percentage: progressPercent(delivered, total),
    return_progress_percentage: progressPercent(returned, total)
  };
}

function progressPercent(value: number, total: number) {
  return total > 0 ? Math.round((value / total) * 100) : 0;
}
