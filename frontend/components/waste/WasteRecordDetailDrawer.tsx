"use client";

import { FileImage, MapPin, Scale, User } from "lucide-react";
import type { ReactNode } from "react";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { WasteDestinationBadge } from "@/components/waste/WasteDestinationBadge";
import { WasteTypeBadge } from "@/components/waste/WasteTypeBadge";
import type { WasteRecord } from "@/types/waste";

function date(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "-";
}

function recorderLabel(record: WasteRecord) {
  return record.recorder?.full_name || record.recorder?.email || (record.recorded_by ? "Usuario registrado" : "-");
}

export function WasteRecordDetailDrawer({ record, typeLabel, canEdit, canDelete, onClose, onEdit, onDelete }: { record: WasteRecord; typeLabel: string; canEdit: boolean; canDelete: boolean; onClose: () => void; onEdit: () => void; onDelete: () => void }) {
  return (
    <ModalShell title="Detalle de residuo" description="Registro ambiental del evento." onClose={onClose}>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2"><WasteTypeBadge value={typeLabel} /><WasteDestinationBadge destination={record.destination} /></div>
        <Info icon={<Scale className="h-4 w-4" />} label="Peso" value={`${Number(record.weight_kg || 0).toLocaleString("es-CL")} kg`} />
        <Info icon={<MapPin className="h-4 w-4" />} label="Zona" value={record.zone?.name || "Sin zona"} />
        <Info icon={<User className="h-4 w-4" />} label="Registrado por" value={recorderLabel(record)} />
        <Info icon={<FileImage className="h-4 w-4" />} label="Evidencia" value={record.evidence_id ? "Asociada" : "Sin evidencia"} />
        <Info icon={<Scale className="h-4 w-4" />} label="Fecha" value={date(record.recorded_at || record.created_at)} />
        {record.destination_detail ? <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">{record.destination_detail}</div> : null}
        {record.notes ? <div className="rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-900">{record.notes}</div> : null}
        <div className="grid gap-2 md:grid-cols-2">{canEdit ? <Button onClick={onEdit}>Editar</Button> : null}{canDelete ? <Button variant="secondary" onClick={onDelete}>Eliminar</Button> : null}</div>
      </div>
    </ModalShell>
  );
}

function Info({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="flex items-center gap-3 rounded-2xl border p-3 text-sm"><span className="text-emerald-700">{icon}</span><span className="font-semibold">{label}:</span><span className="text-slate-600">{value}</span></div>;
}
