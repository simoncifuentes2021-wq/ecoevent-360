"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { WasteTypeFormModal } from "@/components/waste/WasteTypeFormModal";
import { WasteTypeTable } from "@/components/waste/WasteTypeTable";
import { createWasteType, deleteWasteType, getWasteTypes, updateWasteType } from "@/lib/api/wasteTypes";
import type { WasteType, WasteTypeCreate, WasteTypeUpdate } from "@/types/waste";

export default function WasteTypesPage() {
  const [items, setItems] = useState<WasteType[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendUnavailable, setBackendUnavailable] = useState(false);
  const [formItem, setFormItem] = useState<WasteType | null | undefined>();
  const [deleting, setDeleting] = useState<WasteType | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await getWasteTypes());
      setBackendUnavailable(false);
    } catch (err) {
      setBackendUnavailable(true);
      setError(err instanceof Error ? err.message : "El catalogo no esta disponible.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function save(data: WasteTypeCreate | WasteTypeUpdate) {
    setSaving(true);
    try {
      if (formItem) await updateWasteType(formItem.id, data);
      else await createWasteType(data as WasteTypeCreate);
      setFormItem(undefined);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    await deleteWasteType(deleting.id);
    setDeleting(null);
    await load();
  }

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader title="Tipos de residuos" description="Catalogo ambiental usado para clasificar registros de eventos." actions={!backendUnavailable ? <Button onClick={() => setFormItem(null)}><Plus className="h-4 w-4" />Crear tipo</Button> : null} />
        {loading ? <LoadingState label="Cargando tipos..." /> : null}
        {backendUnavailable ? <EmptyState title="Catalogo no disponible" description="El catalogo de tipos de residuos aun no esta disponible en el backend. Actualmente se usan tipos predefinidos." /> : null}
        {!backendUnavailable && error ? <ErrorState message={error} onRetry={load} /> : null}
        {!backendUnavailable && !loading ? <WasteTypeTable items={items} onDelete={setDeleting} onEdit={setFormItem} /> : null}
        {formItem !== undefined ? <WasteTypeFormModal item={formItem} loading={saving} onClose={() => setFormItem(undefined)} onSubmit={save} /> : null}
        <ConfirmDialog open={Boolean(deleting)} title="Eliminar tipo" description="El tipo se eliminara o desactivara si el backend lo permite." onClose={() => setDeleting(null)} onConfirm={confirmDelete} />
      </div>
    </RoleGuard>
  );
}
