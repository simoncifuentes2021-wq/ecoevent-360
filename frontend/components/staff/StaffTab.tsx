"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarSync, UserPlus } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { AssignStaffModal } from "@/components/staff/AssignStaffModal";
import { StaffTable } from "@/components/staff/StaffTable";
import { Button } from "@/components/ui/button";
import { assignEventStaff, getEventStaff, removeEventStaff, syncEventCalendarInvitations } from "@/lib/api/staff";
import { getEventSessions } from "@/lib/api/eventSessions";
import { getShowStaff, removeShowStaff } from "@/lib/api/showOperations";
import { getUsers } from "@/lib/api/users";
import { canAssignStaff, canManageStaff } from "@/lib/permissions";
import type { UserRole } from "@/types/roles";
import type { EventStaff, EventStaffCreate } from "@/types/staff";
import type { User } from "@/types/user";
import type { EventSession } from "@/types/eventSession";
import { FilterSelect } from "@/components/common/FilterSelect";

export function StaffTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [staff, setStaff] = useState<EventStaff[]>([]);
  const [sessions, setSessions] = useState<EventSession[]>([]);
  const [context, setContext] = useState("all");
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncingInvitations, setSyncingInvitations] = useState(false);
  const [invitationMessage, setInvitationMessage] = useState<{ ok: boolean; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [assignOpen, setAssignOpen] = useState(false);
  const [removing, setRemoving] = useState<EventStaff | null>(null);
  const canManage = canManageStaff(role);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [staffData, sessionData] = await Promise.all([getEventStaff(eventId), getEventSessions(eventId)]);
      setSessions(sessionData);
      const eventStaffById = new Map(staffData.map((item) => [item.id, item]));
      const showAssignments = role === "CLIENT" ? [] : (await Promise.all(sessionData.map(async (session) => ({ session, items: (await getShowStaff(session.id)).items })))).flatMap(({ session, items }) => items.map((item) => {
        const eventStaff = eventStaffById.get(item.event_staff_id);
        return { id: item.event_staff_id, event_id: item.event_id, user_id: item.user?.id || "", user: item.user, role_in_event: item.operational_role, shift_start: item.shift_start, shift_end: item.shift_end, calendar_invitation_status: eventStaff?.calendar_invitation_status, calendar_invitation_error: eventStaff?.calendar_invitation_error, calendar_invitation_sent_at: eventStaff?.calendar_invitation_sent_at, session_id: item.session_id, session_name: item.session_name || session.name, show_assignment_id: item.id };
      }));
      setStaff([...staffData.map((item) => ({ ...item, session_id: null, session_name: null })), ...showAssignments]);
      try {
        const userData = await loadAssignableUsers(role);
        setUsers(
          userData.filter((user) => {
            const isAssignable = user.role === "ADMIN" || user.role === "WORKER" || user.role === "SUPERVISOR" || user.role === "LOGISTICS_OPERATOR";
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
    if (removing.show_assignment_id) await removeShowStaff(removing.show_assignment_id);
    else await removeEventStaff(eventId, removing.user_id);
    setRemoving(null);
    await load();
  }

  async function syncInvitations() {
    setSyncingInvitations(true);
    setInvitationMessage(null);
    try {
      const result = await syncEventCalendarInvitations(eventId);
      setInvitationMessage({ ok: result.ok, message: result.message });
      await load();
    } catch (cause) {
      setInvitationMessage({ ok: false, message: cause instanceof Error ? cause.message : "No se pudieron actualizar las invitaciones." });
    } finally {
      setSyncingInvitations(false);
    }
  }

  const filteredStaff = useMemo(() => staff.filter((item) => context === "all" || (context === "general" ? !item.session_id : item.session_id === context)), [context, staff]);
  const hasPendingInvitations = staff.some((item) => item.calendar_invitation_status !== "SENT" && item.calendar_invitation_status !== "CANCELLED");

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-950">Personal asignado</h2>
          <p className="text-sm text-slate-600">Las invitaciones de calendario se envían al asignar personal. Aquí puedes revisar su estado.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {canManage && staff.length > 0 ? <Button variant="secondary" disabled={syncingInvitations} onClick={() => void syncInvitations()}><CalendarSync className={`h-4 w-4 ${syncingInvitations ? "animate-spin" : ""}`} />{syncingInvitations ? "Enviando..." : hasPendingInvitations ? "Enviar o reintentar invitaciones" : "Actualizar invitación"}</Button> : null}
          {canAssignStaff(role) ? <Button onClick={() => setAssignOpen(true)}><UserPlus className="h-4 w-4" />Asignar personal</Button> : null}
        </div>
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {invitationMessage ? <div className={`rounded-xl border p-3 text-sm ${invitationMessage.ok ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-rose-200 bg-rose-50 text-rose-900"}`}>{invitationMessage.message}</div> : null}
      {sessions.length ? <div className="max-w-xs"><FilterSelect label="Contexto" value={context} onChange={setContext} options={[{ label: "Todos", value: "all" }, { label: "General", value: "general" }, ...sessions.map((session) => ({ label: session.name, value: session.id }))]} /></div> : null}
      <StaffTable canManage={canManage} canRemove={(item) => item.show_assignment_id ? canManage : role === "SUPER_ADMIN" || role === "ADMIN"} error={null} loading={loading} staff={filteredStaff} onRemove={setRemoving} />
      {assignOpen ? <AssignStaffModal assigned={staff.filter((item) => !item.session_id)} loading={saving} users={users} onClose={() => setAssignOpen(false)} onSubmit={assign} /> : null}
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
