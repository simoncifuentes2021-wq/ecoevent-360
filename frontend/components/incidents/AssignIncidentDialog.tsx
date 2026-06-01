"use client";

import { useState } from "react";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import type { EventStaff } from "@/types/staff";

export function AssignIncidentDialog({ staff, loading, onClose, onConfirm }: { staff: EventStaff[]; loading?: boolean; onClose: () => void; onConfirm: (userId: string) => Promise<void> }) {
  const [userId, setUserId] = useState("");
  return (
    <ModalShell title="Asignar responsable" description="Selecciona una persona del equipo del evento." onClose={onClose}>
      <div className="space-y-4">
        <select className="h-12 w-full rounded-2xl border px-4" value={userId} onChange={(event) => setUserId(event.target.value)}>
          <option value="">Seleccionar</option>
          {staff.map((item) => <option key={item.user_id} value={item.user_id}>{item.user?.full_name || item.user_id}</option>)}
        </select>
        <div className="flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={!userId || loading} onClick={() => onConfirm(userId)}>{loading ? "Asignando..." : "Asignar"}</Button></div>
      </div>
    </ModalShell>
  );
}
