"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Boxes, Edit, Power, Plus, UserPlus, X } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusBadge } from "@/components/common/StatusBadge";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { getUsers } from "@/lib/api/users";
import {
  assignWarehouseUser,
  createWarehouse,
  deactivateWarehouse,
  getWarehouseUsers,
  getWarehouses,
  removeWarehouseUser,
  updateWarehouseUser,
  updateWarehouse
} from "@/lib/api/warehouses";
import type { User } from "@/types/user";
import type { Warehouse, WarehouseCreate, WarehouseUser } from "@/types/warehouse";

const limit = 20;

type WarehouseFormState = {
  name: string;
  address: string;
  city: string;
  notes: string;
  is_active: boolean;
};

export default function AdminWarehousesPage() {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formTarget, setFormTarget] = useState<Warehouse | null | undefined>(undefined);
  const [deactivating, setDeactivating] = useState<Warehouse | null>(null);
  const [assigning, setAssigning] = useState<Warehouse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getWarehouses({ page, limit });
      setWarehouses(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar las bodegas.");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveWarehouse(data: WarehouseCreate & { is_active?: boolean }) {
    if (formTarget) {
      await updateWarehouse(formTarget.id, data);
    } else {
      await createWarehouse(data);
    }
    setFormTarget(undefined);
    await load();
  }

  async function confirmDeactivate() {
    if (!deactivating) return;
    await deactivateWarehouse(deactivating.id);
    setDeactivating(null);
    await load();
  }

  const columns: DataTableColumn<Warehouse>[] = [
    { key: "name", header: "Bodega", cell: (warehouse) => <span className="font-semibold">{warehouse.name}</span> },
    { key: "city", header: "Ciudad", cell: (warehouse) => warehouse.city || "-" },
    { key: "address", header: "Direccion", cell: (warehouse) => warehouse.address || "-" },
    { key: "is_active", header: "Estado", cell: (warehouse) => <StatusBadge status={warehouse.is_active ? "ACTIVE" : "INACTIVE"} /> }
  ];

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Bodegas"
          description="Administra bodegas logisticas disponibles para futuras etapas de stock."
          actions={
            <Button onClick={() => setFormTarget(null)} type="button">
              <Plus className="h-4 w-4" />
              Crear bodega
            </Button>
          }
        />
        <DataTable
          actions={(warehouse) => (
            <div className="flex justify-end gap-2">
              <Link href={`/admin/stock?warehouse_id=${warehouse.id}`}>
                <Button size="sm" type="button" variant="secondary">
                  <Boxes className="h-4 w-4" />
                </Button>
              </Link>
              <Button size="sm" type="button" variant="secondary" onClick={() => setAssigning(warehouse)}>
                <UserPlus className="h-4 w-4" />
                Permisos
              </Button>
              <Button size="sm" type="button" variant="secondary" onClick={() => setFormTarget(warehouse)}>
                <Edit className="h-4 w-4" />
              </Button>
              {warehouse.is_active ? (
                <Button size="sm" type="button" variant="ghost" onClick={() => setDeactivating(warehouse)}>
                  <Power className="h-4 w-4" />
                </Button>
              ) : null}
            </div>
          )}
          columns={columns}
          data={warehouses}
          emptyTitle="Sin bodegas"
          emptyDescription="Crea la primera bodega para preparar la configuracion logistica."
          error={error}
          getRowKey={(warehouse) => warehouse.id}
          limit={limit}
          loading={loading}
          onPageChange={setPage}
          page={page}
          total={total}
        />
        {formTarget !== undefined ? (
          <WarehouseFormModal
            initialData={formTarget || undefined}
            onClose={() => setFormTarget(undefined)}
            onSubmit={saveWarehouse}
          />
        ) : null}
        {assigning ? (
          <WarehouseUsersModal warehouse={assigning} onClose={() => setAssigning(null)} />
        ) : null}
        <ConfirmDialog
          description={`La bodega ${deactivating?.name || ""} quedara inactiva, pero se conservara su historial.`}
          open={Boolean(deactivating)}
          title="Desactivar bodega"
          onClose={() => setDeactivating(null)}
          onConfirm={confirmDeactivate}
        />
      </div>
    </RoleGuard>
  );
}

function WarehouseFormModal({
  initialData,
  onClose,
  onSubmit
}: {
  initialData?: Warehouse;
  onClose: () => void;
  onSubmit: (data: WarehouseCreate & { is_active?: boolean }) => Promise<void>;
}) {
  const [form, setForm] = useState<WarehouseFormState>({
    name: initialData?.name || "",
    address: initialData?.address || "",
    city: initialData?.city || "",
    notes: initialData?.notes || "",
    is_active: initialData?.is_active ?? true
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = form.name.trim().length > 0;

  async function submit() {
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        name: form.name.trim(),
        address: form.address || null,
        city: form.city || null,
        notes: form.notes || null,
        is_active: form.is_active
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo guardar la bodega.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell
      title={initialData ? "Editar bodega" : "Crear bodega"}
      description="Configura los datos base de la bodega."
      onClose={onClose}
    >
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        {error ? <ErrorState message={error} /> : null}
        <label className="grid gap-2 text-sm font-semibold">
          Nombre
          <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Direccion
          <Input value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Ciudad
          <Input value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Observaciones
          <textarea
            className="min-h-24 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            value={form.notes}
            onChange={(event) => setForm({ ...form, notes: event.target.value })}
          />
        </label>
        <label className="flex items-center gap-2 text-sm font-semibold">
          <input
            checked={form.is_active}
            className="h-4 w-4"
            type="checkbox"
            onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
          />
          Bodega activa
        </label>
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={!valid || saving} type="submit">
            {saving ? "Guardando..." : "Guardar"}
          </Button>
        </div>
      </form>
    </ModalShell>
  );
}

function WarehouseUsersModal({ warehouse, onClose }: { warehouse: Warehouse; onClose: () => void }) {
  const [assignments, setAssignments] = useState<WarehouseUser[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [canViewStock, setCanViewStock] = useState(true);
  const [canManageStock, setCanManageStock] = useState(false);
  const [canDispatchOrders, setCanDispatchOrders] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const assignedIds = useMemo(() => new Set(assignments.map((assignment) => assignment.user_id)), [assignments]);
  const options = useMemo(
    () => users.filter((user) => user.is_active && ["LOGISTICS_OPERATOR", "ADMIN", "SUPER_ADMIN"].includes(user.role) && !assignedIds.has(user.id)),
    [assignedIds, users]
  );
  const hasAssignableUsers = options.length > 0;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [assignmentData, userData] = await Promise.all([
        getWarehouseUsers(warehouse.id),
        getUsers({ is_active: "true", page: 1, limit: 100 })
      ]);
      setAssignments(assignmentData);
      setUsers(userData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar operadores.");
    } finally {
      setLoading(false);
    }
  }, [warehouse.id]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (selectedUserId && options.some((user) => user.id === selectedUserId)) return;
    setSelectedUserId(options[0]?.id || "");
  }, [options, selectedUserId]);

  async function assign() {
    if (!selectedUserId) return;
    setSaving(true);
    setError(null);
    try {
      await assignWarehouseUser(warehouse.id, {
        user_id: selectedUserId,
        can_view_stock: canViewStock,
        can_manage_stock: canManageStock,
        can_dispatch_orders: canDispatchOrders
      });
      setCanViewStock(true);
      setCanManageStock(false);
      setCanDispatchOrders(true);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo asignar el usuario.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(userId: string) {
    setSaving(true);
    setError(null);
    try {
      await removeWarehouseUser(warehouse.id, userId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo quitar el usuario.");
    } finally {
      setSaving(false);
    }
  }

  async function updatePermissions(
    assignment: WarehouseUser,
    changes: {
      can_view_stock?: boolean;
      can_manage_stock?: boolean;
      can_dispatch_orders?: boolean;
    }
  ) {
    setSaving(true);
    setError(null);
    try {
      const next = {
        can_view_stock: changes.can_view_stock ?? assignment.can_view_stock,
        can_manage_stock: changes.can_manage_stock ?? assignment.can_manage_stock,
        can_dispatch_orders: changes.can_dispatch_orders ?? assignment.can_dispatch_orders
      };
      if (!next.can_view_stock) {
        next.can_manage_stock = false;
      }
      await updateWarehouseUser(warehouse.id, assignment.user_id, next);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudieron actualizar los permisos.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Permisos de bodega" description={`Bodega: ${warehouse.name}`} size="lg" onClose={onClose}>
      <div className="space-y-4">
        {error ? <ErrorState message={error} /> : null}
        <div className="rounded-lg border bg-slate-50 p-3 sm:p-4">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900">Asignar usuario a esta bodega</p>
              <p className="text-xs text-slate-500">
                Solo aparecen usuarios activos con rol logistico o administrador que aun no estan asignados.
              </p>
            </div>
            <Link className="text-xs font-semibold text-primary hover:underline" href="/admin/usuarios/nuevo">
              Crear usuario
            </Link>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto]">
            <select
              className="h-10 rounded-md border bg-white px-3 text-sm"
              disabled={loading || saving || !hasAssignableUsers}
              value={selectedUserId}
              onChange={(event) => setSelectedUserId(event.target.value)}
            >
              <option value="">{hasAssignableUsers ? "Seleccionar operador" : "Sin usuarios disponibles"}</option>
              {options.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name} - {user.role}
                </option>
              ))}
            </select>
            <Button disabled={!selectedUserId || saving || !canViewStock} type="button" onClick={assign}>
              <UserPlus className="h-4 w-4" />
              {saving ? "Asignando..." : "Asignar permisos"}
            </Button>
          </div>
          {!loading && !hasAssignableUsers ? (
            <p className="mt-2 text-xs font-semibold text-amber-700">
              Todos los usuarios disponibles ya tienen permisos en esta bodega o no hay operadores activos para asignar.
            </p>
          ) : null}
          <div className="mt-3 grid gap-2 text-sm md:grid-cols-3">
            <label className="flex items-center gap-2 font-semibold">
              <input
                checked={canViewStock}
                className="h-4 w-4"
                type="checkbox"
                onChange={(event) => {
                  setCanViewStock(event.target.checked);
                  if (!event.target.checked) setCanManageStock(false);
                }}
              />
              Ver stock
            </label>
            <label className="flex items-center gap-2 font-semibold">
              <input
                checked={canManageStock}
                className="h-4 w-4"
                disabled={!canViewStock}
                type="checkbox"
                onChange={(event) => setCanManageStock(event.target.checked)}
              />
              Crear movimientos
            </label>
            <label className="flex items-center gap-2 font-semibold">
              <input
                checked={canDispatchOrders}
                className="h-4 w-4"
                type="checkbox"
                onChange={(event) => setCanDispatchOrders(event.target.checked)}
              />
              Despachar pedidos
            </label>
          </div>
          {!canViewStock ? (
            <p className="mt-2 text-xs font-semibold text-amber-700">Para esta etapa el operador debe tener Ver stock activo.</p>
          ) : null}
        </div>
        <div className="rounded-lg border">
          {loading ? (
            <p className="p-4 text-sm text-slate-500">Cargando operadores...</p>
          ) : assignments.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">No hay operadores asignados.</p>
          ) : (
            <div className="divide-y">
              {assignments.map((assignment) => (
                <div className="grid gap-3 p-3 md:grid-cols-[1fr_auto]" key={assignment.id}>
                  <div>
                    <p className="font-semibold">{assignment.user_full_name || assignment.user_email}</p>
                    <p className="text-xs text-slate-500">{assignment.user_role}</p>
                    <div className="mt-3 grid gap-2 text-sm md:grid-cols-3">
                      <label className="flex items-center gap-2 font-semibold">
                        <input
                          checked={assignment.can_view_stock}
                          className="h-4 w-4"
                          disabled={saving}
                          type="checkbox"
                          onChange={(event) => void updatePermissions(assignment, { can_view_stock: event.target.checked })}
                        />
                        Ver stock
                      </label>
                      <label className="flex items-center gap-2 font-semibold">
                        <input
                          checked={assignment.can_manage_stock}
                          className="h-4 w-4"
                          disabled={saving || !assignment.can_view_stock}
                          type="checkbox"
                          onChange={(event) => void updatePermissions(assignment, { can_manage_stock: event.target.checked })}
                        />
                        Crear movimientos
                      </label>
                      <label className="flex items-center gap-2 font-semibold">
                        <input
                          checked={assignment.can_dispatch_orders}
                          className="h-4 w-4"
                          disabled={saving}
                          type="checkbox"
                          onChange={(event) => void updatePermissions(assignment, { can_dispatch_orders: event.target.checked })}
                        />
                        Despacho
                      </label>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Badge tone={assignment.can_view_stock ? "success" : "neutral"}>{assignment.can_view_stock ? "Puede ver stock" : "Sin ver stock"}</Badge>
                      <Badge tone={assignment.can_manage_stock ? "success" : "neutral"}>{assignment.can_manage_stock ? "Puede crear movimientos" : "Sin movimientos"}</Badge>
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <Button disabled={saving} size="sm" type="button" variant="ghost" onClick={() => void remove(assignment.user_id)}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </ModalShell>
  );
}
