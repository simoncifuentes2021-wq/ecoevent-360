"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Edit, PackagePlus, Search, Trash2 } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createCatalogItem, deactivateCatalogItem, getCatalogItems, updateCatalogItem } from "@/lib/api/orders";
import type { CatalogItem, CatalogItemCreate } from "@/types/order";
import { money } from "@/components/orders/order-ui";

const emptyForm: CatalogItemCreate = {
  name: "",
  category: "",
  description: "",
  unit: "",
  default_unit_price: 0,
  is_active: true
};

export function CatalogItemsPage() {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [active, setActive] = useState("true");
  const [editing, setEditing] = useState<CatalogItem | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const categories = useMemo(() => Array.from(new Set(items.map((item) => item.category).filter(Boolean))) as string[], [items]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCatalogItems({ q, category, is_active: active === "" ? undefined : active, page: 1, limit: 100 });
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el catálogo.");
    } finally {
      setLoading(false);
    }
  }, [active, category, q]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(data: CatalogItemCreate) {
    setSaving(true);
    try {
      const payload = {
        ...data,
        category: data.category || null,
        description: data.description || null,
        unit: data.unit || null,
        default_unit_price: data.default_unit_price ?? 0
      };
      if (editing) await updateCatalogItem(editing.id, payload);
      else await createCatalogItem(payload);
      setFormOpen(false);
      setEditing(null);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function deactivate(item: CatalogItem) {
    await deactivateCatalogItem(item.id);
    await load();
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Catálogo de elementos"
        description="Elementos físicos disponibles para armar pedidos logísticos."
        actions={
          <Button onClick={() => { setEditing(null); setFormOpen(true); }} type="button">
            <PackagePlus className="h-4 w-4" />
            Crear elemento
          </Button>
        }
      />
      <Card>
        <CardContent className="grid gap-3 p-4 md:grid-cols-4">
          <label className="relative md:col-span-2">
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <Input className="pl-9" placeholder="Buscar elemento" value={q} onChange={(event) => setQ(event.target.value)} />
          </label>
          <select className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm" value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">Todas las categorías</option>
            {categories.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <select className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm" value={active} onChange={(event) => setActive(event.target.value)}>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
            <option value="">Todos</option>
          </select>
        </CardContent>
      </Card>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!loading && !error ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[780px] text-left text-sm">
                <thead className="border-b text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-5 py-3">Elemento</th>
                    <th className="px-5 py-3">Categoría</th>
                    <th className="px-5 py-3">Unidad</th>
                    <th className="px-5 py-3">Precio</th>
                    <th className="px-5 py-3">Estado</th>
                    <th className="px-5 py-3 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr className="border-b last:border-0" key={item.id}>
                      <td className="px-5 py-3"><p className="font-semibold">{item.name}</p><p className="text-xs text-slate-500">{item.description || ""}</p></td>
                      <td className="px-5 py-3">{item.category || "-"}</td>
                      <td className="px-5 py-3">{item.unit || "-"}</td>
                      <td className="px-5 py-3">{money(item.default_unit_price)}</td>
                      <td className="px-5 py-3">{item.is_active ? "Activo" : "Inactivo"}</td>
                      <td className="px-5 py-3">
                        <div className="flex justify-end gap-2">
                          <Button size="sm" variant="secondary" onClick={() => { setEditing(item); setFormOpen(true); }}><Edit className="h-4 w-4" />Editar</Button>
                          {item.is_active ? <Button size="sm" variant="secondary" onClick={() => deactivate(item)}><Trash2 className="h-4 w-4" />Desactivar</Button> : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {items.length === 0 ? <div className="p-8 text-center text-sm text-slate-500">No hay elementos con los filtros actuales.</div> : null}
            </div>
          </CardContent>
        </Card>
      ) : null}
      {formOpen ? <CatalogItemForm item={editing} loading={saving} onClose={() => setFormOpen(false)} onSubmit={submit} /> : null}
    </div>
  );
}

function CatalogItemForm({ item, loading, onClose, onSubmit }: { item: CatalogItem | null; loading: boolean; onClose: () => void; onSubmit: (data: CatalogItemCreate) => Promise<void> }) {
  const [form, setForm] = useState<CatalogItemCreate>(item ? {
    name: item.name,
    category: item.category || "",
    description: item.description || "",
    unit: item.unit || "",
    default_unit_price: Number(item.default_unit_price || 0),
    is_active: item.is_active
  } : emptyForm);
  const valid = form.name.trim().length > 0 && Number(form.default_unit_price || 0) >= 0;

  return (
    <ModalShell title={item ? "Editar elemento" : "Crear elemento"} onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); if (valid) void onSubmit(form); }}>
        <label className="grid gap-2 text-sm font-semibold">Nombre<Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">Categoría<Input value={form.category || ""} onChange={(event) => setForm({ ...form, category: event.target.value })} /></label>
          <label className="grid gap-2 text-sm font-semibold">Unidad<Input value={form.unit || ""} onChange={(event) => setForm({ ...form, unit: event.target.value })} /></label>
        </div>
        <label className="grid gap-2 text-sm font-semibold">Precio unitario por defecto<Input min={0} type="number" value={form.default_unit_price ?? 0} onChange={(event) => setForm({ ...form, default_unit_price: Number(event.target.value) })} /></label>
        <label className="grid gap-2 text-sm font-semibold">Descripción<Input value={form.description || ""} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
        <label className="flex items-center gap-2 text-sm font-semibold"><input checked={form.is_active ?? true} type="checkbox" onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />Activo</label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || loading} type="submit">{loading ? "Guardando..." : "Guardar"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}
