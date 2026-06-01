"use client";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { QrCodeCard } from "@/components/qr/QrCodeCard";
import type { QrCode } from "@/types/qr";

export function QrCodeTable({ qrCodes, loading, error, onDownload }: { qrCodes: QrCode[]; loading?: boolean; error?: string | null; onDownload: (qr: QrCode) => void }) {
  const columns: DataTableColumn<QrCode>[] = [
    { key: "label", header: "Etiqueta", cell: (qr) => qr.label },
    { key: "zone", header: "Zona", cell: (qr) => qr.zone?.name || "General" },
    { key: "target", header: "Destino", cell: (qr) => qr.target_url || qr.file_url || "Sin URL" }
  ];

  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:hidden">
        {qrCodes.map((qr) => <QrCodeCard key={qr.id} qr={qr} onDownload={onDownload} />)}
      </div>
      <div className="hidden md:block">
        <DataTable columns={columns} data={qrCodes} emptyTitle="No hay QR generados" error={error} loading={loading} actions={(qr) => <button className="text-sm font-semibold text-emerald-700" onClick={() => onDownload(qr)} type="button">Descargar</button>} />
      </div>
    </div>
  );
}
