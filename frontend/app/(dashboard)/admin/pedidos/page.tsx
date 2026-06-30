"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Eye, PackageCheck, Plus, Search } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { OrderStatusBadge, ProgressLine, dateValue, money, numberValue, orderStatusLabels } from "@/components/orders/order-ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getEvents } from "@/lib/api/events";
import { getCatalogItems, getEventOrders, createEventOrder, createOrderItem } from "@/lib/api/orders";
import { getEventStaff } from "@/lib/api/staff";
import type { Event } from "@/types/event";
import type { CatalogItem, EventOrder, EventOrderCreate, EventOrderItemCreate, OrderStatus } from "@/types/order";
import type { EventStaff } from "@/types/staff";

type OrderRow = EventOrder & { eventName: string };
type QuickItem = { catalog_item_id: string; name: string; quantity: string; unit: string };

const statuses: OrderStatus[] = ["DRAFT", "REQUESTED", "APPROVED", "PREPARING", "LOADED", "IN_TRANSIT", "DELIVERED", "RETURN_IN_PROGRESS", "RETURNED", "CLOSED", "CANCELLED"];

export default function AdminOrdersPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const eventResponse = await getEvents({ page: 1, limit: 100 });
      const eventItems = eventResponse.items;
      const orderResponses = await Promise.all(
        eventItems.map((event) =>
          getEventOrders(event.id, { page: 1, limit: 50 })
            .then((response) => response.items.map((order) => ({ ...order, eventName: event.name })))
            .catch(() => [])
        )
      );
      setEvents(eventItems);
      setOrders(orderResponses.flat().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar pedidos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => orders.filter((order) => {
    const text = `${order.title} ${order.eventName} ${order.assignee?.full_name || ""}`.toLowerCase();
    return (!q || text.includes(q.toLowerCase())) && (!status || order.status === status);
  }), [orders, q, status]);

  const activeCount = orders.filter((order) => !["CLOSED", "CANCELLED", "RETURNED"].includes(order.status)).length;
  const assignedCount = orders.filter((order) => Boolean(order.assigned_to)).length;

  async function createQuickOrder(eventId: string, data: EventOrderCreate, items: EventOrderItemCreate[]) {
    const order = await createEventOrder(eventId, data);
    if (items.length > 0) await Promise.all(items.map((item) => createOrderItem(order.id, item)));
    setFormOpen(false);
    await load();
  }

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN", "SUPERVISOR"]}>
      <div className="space-y-6">
        <PageHeader
          title="Pedidos logísticos"
          description="Bandeja global para crear, asignar y seguir pedidos de todos los eventos."
          actions={
            <Button onClick={() => setFormOpen(true)} type="button">
              <Plus className="h-4 w-4" />
              Crear pedido
            </Button>
          }
        />

        <div className="grid gap-3 md:grid-cols-3">
          <Metric label="Pedidos totales" value={orders.length} />
          <Metric label="Activos" value={activeCount} />
          <Metric label="Asignados" value={assignedCount} />
        </div>

        <Card>
          <CardContent className="grid gap-3 p-4 md:grid-cols-[1fr_240px]">
            <label className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <Input className="pl-9" placeholder="Buscar por pedido, evento o encargado" value={q} onChange={(event) => setQ(event.target.value)} />
            </label>
            <select className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm" value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">Todos los estados</option>
              {statuses.map((item) => <option key={item} value={item}>{orderStatusLabels[item]}</option>)}
            </select>
          </CardContent>
        </Card>

        {loading ? <LoadingState label="Cargando pedidos..." /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {!loading && !error && filtered.length === 0 ? <EmptyState icon={<PackageCheck className="h-6 w-6" />} title="Sin pedidos logísticos" description="Crea el primer pedido desde esta pantalla y asígnalo a un encargado." /> : null}
        {!loading && !error && filtered.length > 0 ? (
          <div className="grid gap-3">
            {filtered.map((order) => <OrderCard key={order.id} order={order} />)}
          </div>
        ) : null}

        {formOpen ? <QuickOrderModal events={events} onClose={() => setFormOpen(false)} onSubmit={createQuickOrder} /> : null}
      </div>
    </RoleGuard>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <Card><CardContent className="p-4"><p className="text-sm font-semibold text-slate-500">{label}</p><p className="mt-2 text-3xl font-bold text-slate-950">{value}</p></CardContent></Card>;
}

function OrderCard({ order }: { order: OrderRow }) {
  return (
    <Card>
      <CardContent className="grid gap-4 p-5 lg:grid-cols-[1.2fr_1fr_auto] lg:items-center">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <OrderStatusBadge status={order.status} />
            <p className="font-bold text-slate-950">{order.title}</p>
          </div>
          <p className="mt-2 text-sm text-slate-600">{order.eventName} · Encargado: {order.assignee?.full_name || "Sin asignar"} · {dateValue(order.required_date)}</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">Total: {money(order.total_amount)}</p>
        </div>
        <div className="grid gap-2">
          <ProgressLine label="Carga" value={order.progress.load_progress_percentage} count={`${order.progress.loaded_items}/${order.progress.total_items}`} />
          <ProgressLine label="Entrega" value={order.progress.delivery_progress_percentage} count={`${order.progress.delivered_items}/${order.progress.total_items}`} />
          <ProgressLine label="Retorno" value={order.progress.return_progress_percentage} count={`${order.progress.returned_items}/${order.progress.total_items}`} />
        </div>
        <Link href={`/admin/pedidos/${order.id}`}>
          <Button variant="secondary"><Eye className="h-4 w-4" />Abrir</Button>
        </Link>
      </CardContent>
    </Card>
  );
}

function QuickOrderModal({ events, onClose, onSubmit }: { events: Event[]; onClose: () => void; onSubmit: (eventId: string, data: EventOrderCreate, items: EventOrderItemCreate[]) => Promise<void> }) {
  const [eventId, setEventId] = useState(events[0]?.id || "");
  const [staff, setStaff] = useState<EventStaff[]>([]);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [selected, setSelected] = useState<Record<string, QuickItem>>({});
  const [query, setQuery] = useState("");
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<EventOrderCreate>({ title: "Viaje logístico", assigned_to: "", required_date: "", notes: "", description: "" });

  useEffect(() => {
    async function loadContext() {
      const [catalogData, staffData] = await Promise.all([
        getCatalogItems({ is_active: "true", page: 1, limit: 100 }),
        eventId ? getEventStaff(eventId) : Promise.resolve([])
      ]);
      setCatalog(catalogData.items);
      setStaff(staffData);
    }
    void loadContext();
  }, [eventId]);

  const assignees = staff.filter((item) => item.user && ["SUPERVISOR", "LOGISTICS_OPERATOR"].includes(item.user.role));
  const selectedItems = Object.values(selected);
  const filteredCatalog = catalog.filter((item) => `${item.name} ${item.category || ""}`.toLowerCase().includes(query.toLowerCase()));
  const valid = Boolean(eventId && form.title?.trim());

  function toggleItem(item: CatalogItem) {
    setSelected((current) => {
      if (current[item.id]) {
        const next = { ...current };
        delete next[item.id];
        return next;
      }
      return { ...current, [item.id]: { catalog_item_id: item.id, name: item.name, quantity: "1", unit: item.unit || "" } };
    });
  }

  function updateItem(id: string, patch: Partial<QuickItem>) {
    setSelected((current) => ({ ...current, [id]: { ...current[id], ...patch } }));
  }

  async function submit() {
    setSaving(true);
    try {
      await onSubmit(eventId, {
        title: form.title,
        assigned_to: form.assigned_to || null,
        required_date: form.required_date || null,
        description: form.description || null,
        notes: form.notes || null
      }, selectedItems.map((item) => ({
        catalog_item_id: item.catalog_item_id,
        quantity: Number(item.quantity || 0),
        notes: null
      })));
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Crear pedido directo" description="Elige evento, encargado y elementos sin entrar al detalle del evento." onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); if (valid) void submit(); }}>
        <label className="grid gap-2 text-sm font-semibold">Evento<select className="h-10 rounded-md border px-3" value={eventId} onChange={(event) => { setEventId(event.target.value); setForm({ ...form, assigned_to: "" }); }}><option value="">Seleccionar evento</option>{events.map((event) => <option key={event.id} value={event.id}>{event.name}</option>)}</select></label>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">Título<Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
          <label className="grid gap-2 text-sm font-semibold">Fecha requerida<Input type="datetime-local" value={form.required_date || ""} onChange={(event) => setForm({ ...form, required_date: event.target.value })} /></label>
          <label className="grid gap-2 text-sm font-semibold">Encargado<select className="h-10 rounded-md border px-3" value={form.assigned_to || ""} onChange={(event) => setForm({ ...form, assigned_to: event.target.value })}><option value="">Sin asignar</option>{assignees.map((item) => <option key={item.user_id} value={item.user_id}>{item.user?.full_name} · {item.user?.role}</option>)}</select></label>
          <label className="grid gap-2 text-sm font-semibold">Notas<Input value={form.notes || ""} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
        </div>
        <section className="rounded-lg border">
          <div className="border-b bg-slate-50 p-3">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <p className="text-sm font-bold">{selectedItems.length} elementos - Precio y unidad desde catalogo</p>
              <Input className="md:w-64" placeholder="Buscar elemento" value={query} onChange={(event) => setQuery(event.target.value)} />
            </div>
          </div>
          <div className="max-h-72 space-y-2 overflow-y-auto p-3">
            {filteredCatalog.map((item) => {
              const quickItem = selected[item.id];
              return (
                <div className={`rounded-lg border p-3 ${quickItem ? "border-emerald-200 bg-emerald-50" : "border-slate-200"}`} key={item.id}>
                  <div className="flex items-start gap-3">
                    <input checked={Boolean(quickItem)} className="mt-1 h-4 w-4" type="checkbox" onChange={() => toggleItem(item)} />
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold">{item.name}</p>
                      <p className="text-xs text-slate-500">{item.category || "Sin categoría"} - Unidad: {item.unit || "unidad"}</p>
                      {quickItem ? (
                        <div className="mt-3 grid gap-2 md:grid-cols-[minmax(0,220px)_1fr] md:items-end">
                          <label className="grid gap-1 text-xs font-semibold">
                            Cantidad
                            <Input min={0.01} step="0.01" type="number" value={quickItem.quantity} onChange={(event) => updateItem(item.id, { quantity: cleanQuantityInput(event.target.value) })} onFocus={(event) => event.currentTarget.select()} />
                          </label>
                          <p className="rounded-md bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                            Unidad cargada del catalogo: {quickItem.unit || "unidad"}
                          </p>
                        </div>
                      ) : null}
                    </div>
                    {quickItem ? <span className="text-xs font-bold text-emerald-700">{numberValue(Number(quickItem.quantity || 0))}</span> : null}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Crear pedido"}</Button></div>
      </form>
    </ModalShell>
  );
}

function cleanQuantityInput(value: string) {
  if (!value) return "";
  if (value.includes(".")) {
    const [whole, decimal] = value.split(".", 2);
    return `${whole.replace(/^0+(?=\d)/, "") || "0"}.${decimal}`;
  }
  return value.replace(/^0+(?=\d)/, "");
}
