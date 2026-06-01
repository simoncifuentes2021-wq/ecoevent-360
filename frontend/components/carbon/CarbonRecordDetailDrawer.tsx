"use client";

import { Cloud, FileImage, Scale } from "lucide-react";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { CarbonCategoryBadge } from "@/components/carbon/CarbonCategoryBadge";
import { CarbonScopeBadge } from "@/components/carbon/CarbonScopeBadge";
import { factorValue, recordKg } from "@/components/carbon/CarbonRecordTable";
import { formatKgCO2e } from "@/lib/normalizers/carbon";
import type { CarbonRecord } from "@/types/carbon";

export function CarbonRecordDetailDrawer({ record, canEdit, canDelete, onClose, onEdit, onDelete }: { record: CarbonRecord; canEdit: boolean; canDelete: boolean; onClose: () => void; onEdit: () => void; onDelete: () => void }) {
  return <ModalShell title="Detalle de emision" description={record.source || record.description || "Registro de huella"} onClose={onClose}><div className="space-y-4"><div className="flex gap-2"><CarbonCategoryBadge category={record.category} /><CarbonScopeBadge scope={record.scope} /></div><Info icon={<Scale className="h-4 w-4" />} label="Actividad" value={`${record.activity_value} ${record.activity_unit}`} /><Info icon={<Cloud className="h-4 w-4" />} label="Emisiones" value={formatKgCO2e(recordKg(record))} /><Info icon={<Scale className="h-4 w-4" />} label="Factor" value={factorValue(record).toLocaleString("es-CL", { maximumFractionDigits: 6 })} /><Info icon={<FileImage className="h-4 w-4" />} label="Evidencia" value={record.evidence_id ? "Asociada" : "Sin evidencia"} />{record.notes ? <div className="rounded-2xl bg-slate-50 p-4 text-sm">{record.notes}</div> : null}<div className="grid gap-2 md:grid-cols-2">{canEdit ? <Button onClick={onEdit}>Editar</Button> : null}{canDelete ? <Button variant="secondary" onClick={onDelete}>Eliminar</Button> : null}</div></div></ModalShell>;
}
function Info({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="flex items-center gap-3 rounded-2xl border p-3 text-sm"><span className="text-emerald-700">{icon}</span><span className="font-semibold">{label}:</span><span className="text-slate-600">{value}</span></div>;
}
