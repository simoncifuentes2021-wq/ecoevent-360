"use client";

import { WasteRecordFormModal } from "@/components/waste/WasteRecordFormModal";
import type { Evidence } from "@/types/evidence";
import type { WasteRecordCreate, WasteType } from "@/types/waste";
import type { Zone } from "@/types/zone";

export function MobileWasteForm({ zones, evidences, wasteTypes, loading, onCancel, onSubmit }: { zones: Zone[]; evidences: Evidence[]; wasteTypes: WasteType[]; loading?: boolean; onCancel: () => void; onSubmit: (data: WasteRecordCreate) => Promise<void> }) {
  return <WasteRecordFormModal evidences={evidences} loading={loading} wasteTypes={wasteTypes} zones={zones} onClose={onCancel} onSubmit={(data) => onSubmit(data as WasteRecordCreate)} />;
}
