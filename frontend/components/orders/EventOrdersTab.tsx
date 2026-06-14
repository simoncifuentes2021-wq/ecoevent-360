"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Eye, Plus, Truck } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createEventOrder, createOrderItem, getCatalogItems, getEventOrders } from "@/lib/api/orders";
import { getEventStaff } from "@/lib/api/staff";
import type { CatalogItem, EventOrder, EventOrderCreate, EventOrderItemCreate } from "@/types/order";
import type { UserRole } from "@/types/roles";
import type { EventStaff } from "@/types/staff";
import { dateValue, money, numberValue, OrderStatusBadge, ProgressLine } from "@/components/orders/order-ui";

type QuickItem = {
  catalog_item_id: string;
  name: string;
  quantity: string;
  unit: string;
};

export function EventOrdersTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const canEdit = role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
  const [orders, setOrders] = useState<EventOrder[]>([]);
  const [staff, setStaff] = useState<EventStaff[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const assignees = useMemo(() => staff.filter((item) => item.user && ["WORKER", "SUPERVISOR"].includes(item.user.role)), [staff]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [orderResponse, staffResponse] = await Promise.all([
        getEventOrders(eventId, { page: 1, limit: 50 }),
        canEdit ? getEventStaff(eventId) : Promise.resolve([])
      ]);
      setOrders(orderResponse.items);
      setStaff(staffResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar pedidos.");
    } finally {
      setLoading(false);
    }
  }, [canEdit, eventId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(data: EventOrderCreate, items: EventOrderItemCreate[]) {
    const order = await createEventOrder(eventId, data);
    if (items.length > 0) {
      await Promise.all(items.map((item) => createOrderItem(order.id, item)));
    }
    setFormOpen(false);
    await load();
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        {canEdit ? (
          <Button onClick={() => setFormOpen(true)} type="button">
            <Plus className="h-4 w-4" />
            Crear pedido
          </Button>
        ) : null}
      </div>
      {orders.length === 0 ? (
        <EmptyState
          icon={<Truck className="h-6 w-6" />}
          title="Este evento aún no tiene pedidos logísticos."
          description="Crea una lista manual de elementos físicos para preparar, cargar, entregar y retornar."
        />
      ) : (
        <div className="grid gap-3">
          {orders.map((order) => (
            <Card key={order.id}>
              <CardContent className="grid gap-4 p-5 lg:grid-cols-[1.4fr_1fr_auto] lg:items-center">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <OrderStatusBadge status={order.status} />
                    <p className="font-bold text-slate-950">{order.title}</p>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">
                    Encargado: {order.assignee?.full_name || "Sin asignar"} · Requerido: {dateValue(order.required_date)}
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-800">Total: {money(order.total_amount)}</p>
                </div>
                <div className="grid gap-2">
                  <ProgressLine label="Carga" value={order.progress.load_progress_percentage} count={`${order.progress.loaded_items}/${order.progress.total_items}`} />
                  <ProgressLine label="Entrega" value={order.progress.delivery_progress_percentage} count={`${order.progress.delivered_items}/${order.progress.total_items}`} />
                  <ProgressLine label="Retorno" value={order.progress.return_progress_percentage} count={`${order.progress.returned_items}/${order.progress.total_items}`} />
                </div>
                <Link href={`/admin/pedidos/${order.id}`}>
                  <Button variant="secondary">
                    <Eye className="h-4 w-4" />
                    Ver detalle
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {formOpen ? <QuickOrderForm assignees={assignees} onClose={() => setFormOpen(false)} onSubmit={submit} /> : null}
    </div>
  );
}

function QuickOrderForm({
  assignees,
  onClose,
  onSubmit
}: {
  assignees: EventStaff[];
  onClose: () => void;
  onSubmit: (data: EventOrderCreate, items: EventOrderItemCreate[]) => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [form, setForm] = useState<EventOrderCreate>({
    title: "Viaje logístico",
    description: "",
    assigned_to: "",
    required_date: "",
    notes: ""
  });
  const [selected, setSelected] = useState<Record<string, QuickItem>>({});

  const valid = form.title.trim().length > 0;
  const selectedItems = Object.values(selected);
  const filteredCatalog = catalog.filter((item) => `${item.name} ${item.category || ""}`.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    async function loadCatalog() {
      try {
        const response = await getCatalogItems({ is_active: "true", page: 1, limit: 100 });
        setCatalog(response.items);
      } catch (err) {
        setCatalogError(err instanceof Error ? err.message : "No pudimos cargar el catálogo.");
      }
    }
    void loadCatalog();
  }, []);

  function toggleItem(item: CatalogItem) {
    setSelected((current) => {
      if (current[item.id]) {
        const next = { ...current };
        delete next[item.id];
        return next;
      }
      return {
        ...current,
        [item.id]: {
          catalog_item_id: item.id,
          name: item.name,
          quantity: "1",
          unit: item.unit || ""
        }
      };
    });
  }

  function updateItem(id: string, patch: Partial<QuickItem>) {
    setSelected((current) => ({ ...current, [id]: { ...current[id], ...patch } }));
  }

  async function submit() {
    setSaving(true);
    try {
      await onSubmit(
        {
          title: form.title,
          description: form.description || null,
          assigned_to: form.assigned_to || null,
          required_date: form.required_date || null,
          notes: form.notes || null
        },
        selectedItems.map((item) => ({
          catalog_item_id: item.catalog_item_id,
          quantity: Number(item.quantity || 0),
          notes: null
        }))
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Crear pedido rápido" description="Selecciona los elementos del viaje ahora; después puedes agregar lo que falte." onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); if (valid) void submit(); }}>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Título
            <Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
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
                  {item.user?.full_name} · {item.user?.role}
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
          Descripción
          <Input value={form.description || ""} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        </label>
        {assignees.length === 0 ? <p className="rounded-lg bg-amber-50 p-3 text-sm font-semibold text-amber-800">Primero asigna personal al evento para poder seleccionar un encargado.</p> : null}
        <div className="rounded-lg border border-slate-200">
          <div className="border-b bg-slate-50 p-3">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-bold text-slate-900">Elementos del viaje</p>
                <p className="text-xs text-slate-500">{selectedItems.length} seleccionados · Precio y unidad desde catálogo</p>
              </div>
              <Input className="md:w-64" placeholder="Buscar en catálogo" value={query} onChange={(event) => setQuery(event.target.value)} />
            </div>
            {catalogError ? <p className="mt-2 text-sm font-semibold text-rose-600">{catalogError}</p> : null}
          </div>
          <div className="max-h-80 space-y-2 overflow-y-auto p-3">
            {filteredCatalog.map((item) => {
              const quickItem = selected[item.id];
              return (
                <div className={`rounded-lg border p-3 ${quickItem ? "border-emerald-200 bg-emerald-50/60" : "border-slate-200 bg-white"}`} key={item.id}>
                  <div className="flex items-start gap-3">
                    <input checked={Boolean(quickItem)} className="mt-1 h-4 w-4" type="checkbox" onChange={() => toggleItem(item)} />
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-slate-900">{item.name}</p>
                      <p className="text-xs text-slate-500">{item.category || "Sin categoría"} · Unidad: {item.unit || "unidad"}</p>
                      {quickItem ? (
                        <div className="mt-3 grid gap-2 md:grid-cols-[minmax(0,220px)_1fr] md:items-end">
                          <label className="grid gap-1 text-xs font-semibold text-slate-600">
                            Cantidad
                            <Input min={0.01} step="0.01" type="number" value={quickItem.quantity} onChange={(event) => updateItem(item.id, { quantity: cleanQuantityInput(event.target.value) })} onFocus={(event) => event.currentTarget.select()} />
                          </label>
                          <p className="rounded-md bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                            Unidad cargada del catálogo: {quickItem.unit || "unidad"}
                          </p>
                        </div>
                      ) : null}
                    </div>
                    {quickItem ? <span className="text-xs font-bold text-emerald-700">{numberValue(Number(quickItem.quantity || 0))}</span> : null}
                  </div>
                </div>
              );
            })}
            {filteredCatalog.length === 0 ? <p className="py-6 text-center text-sm text-slate-500">No hay elementos para esa búsqueda.</p> : null}
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : selectedItems.length > 0 ? "Crear pedido con elementos" : "Crear pedido vacío"}</Button>
        </div>
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
