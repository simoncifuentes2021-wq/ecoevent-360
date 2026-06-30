"use client";

import { useCallback, useEffect, useState } from "react";
import { UserPlus } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { AssignStaffModal } from "@/components/staff/AssignStaffModal";
import { StaffTable } from "@/components/staff/StaffTable";
import { Button } from "@/components/ui/button";
import { assignEventStaff, getEventStaff, removeEventStaff } from "@/lib/api/staff";
import { getUsers } from "@/lib/api/users";
import { canAssignStaff, canManageStaff } from "@/lib/permissions";
import type { UserRole } from "@/types/roles";
import type { EventStaff, EventStaffCreate } from "@/types/staff";
import type { User } from "@/types/user";

export function StaffTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [staff, setStaff] = useState<EventStaff[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assignOpen, setAssignOpen] = useState(false);
  const [removing, setRemoving] = useState<EventStaff | null>(null);
  const canManage = canManageStaff(role);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const staffData = await getEventStaff(eventId);
      setStaff(staffData);
      try {
        const userData = await loadAssignableUsers(role);
        setUsers(
          userData.filter((user) => {
            const isAssignable = user.role === "WORKER" || user.role === "SUPERVISOR" || user.role === "LOGISTICS_OPERATOR";
            return user.is_active && isAssignable;
          })
        );
      } catch {
        setUsers([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, [eventId, role]);

  useEffect(() => { void load(); }, [load]);

  async function assign(data: EventStaffCreate) {
    setSaving(true);
    try {
      await assignEventStaff(eventId, data);
      setAssignOpen(false);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function confirmRemove() {
    if (!removing) return;
    await removeEventStaff(eventId, removing.user_id);
    setRemoving(null);
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-950">Personal asignado</h2>
          <p className="text-sm text-slate-600">Equipo operativo habilitado para turnos y tareas.</p>
        </div>
        {canAssignStaff(role) ? <Button onClick={() => setAssignOpen(true)}><UserPlus className="h-4 w-4" />Asignar personal</Button> : null}
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <StaffTable canManage={canManage} error={null} loading={loading} staff={staff} onRemove={setRemoving} />
      {assignOpen ? <AssignStaffModal assigned={staff} loading={saving} users={users} onClose={() => setAssignOpen(false)} onSubmit={assign} /> : null}
      <ConfirmDialog open={Boolean(removing)} title="Quitar personal" description="La persona dejara de estar asignada al evento si no tiene tareas activas." onClose={() => setRemoving(null)} onConfirm={confirmRemove} />
    </div>
  );
}

async function loadAssignableUsers(role?: UserRole | null) {
  if (role === "SUPERVISOR") {
    const responses = await Promise.all([
      getUsers({ role: "SUPERVISOR", is_active: "true", page: 1, limit: 100 }),
      getUsers({ role: "WORKER", is_active: "true", page: 1, limit: 100 }),
      getUsers({ role: "LOGISTICS_OPERATOR", is_active: "true", page: 1, limit: 100 })
    ]);
    return responses.flatMap((response) => response.items);
  }

  const response = await getUsers({ is_active: "true", page: 1, limit: 100 });
  return response.items;
}
