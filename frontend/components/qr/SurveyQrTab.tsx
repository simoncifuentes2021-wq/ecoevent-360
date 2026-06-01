"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { QrCodeFormModal } from "@/components/qr/QrCodeFormModal";
import { QrCodeTable } from "@/components/qr/QrCodeTable";
import { QrFallbackNotice } from "@/components/qr/QrFallbackNotice";
import { Button } from "@/components/ui/button";
import { createSurveyQrCode, downloadQrCode, getSurveyQrCodes } from "@/lib/api/qr";
import type { QrCode, QrCodeCreate } from "@/types/qr";
import type { Survey } from "@/types/survey";
import type { Zone } from "@/types/zone";

export function SurveyQrTab({ survey, zones, canManage }: { survey: Survey; zones: Zone[]; canManage?: boolean }) {
  const [qrCodes, setQrCodes] = useState<QrCode[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fallback, setFallback] = useState(false);
  const [open, setOpen] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getSurveyQrCodes(survey.id);
      setQrCodes(data.items);
      setFallback(false);
    } catch (err) {
      setFallback(true);
      setError(err instanceof Error ? err.message : "La generacion de QR aun no esta disponible en el backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [survey.id]);

  async function create(data: QrCodeCreate) {
    setSaving(true);
    try {
      await createSurveyQrCode(survey.id, data);
      setOpen(false);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function download(qr: QrCode) {
    const response = await downloadQrCode(qr.id);
    const url = response.url || response.file_url || qr.file_url || qr.image_url;
    if (url) window.open(url, "_blank");
  }

  if (fallback) return <QrFallbackNotice googleFormUrl={survey.google_form_url} />;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div><h3 className="font-bold text-slate-950">QR de encuesta</h3><p className="text-sm text-slate-600">Genera enlaces por zona o un QR general.</p></div>
        {canManage ? <Button onClick={() => setOpen(true)} type="button"><Plus className="h-4 w-4" />Crear QR</Button> : null}
      </div>
      {error ? <ErrorState message={error} title="QR no disponible" /> : null}
      <QrCodeTable error={null} loading={loading} qrCodes={qrCodes} onDownload={download} />
      {open ? <QrCodeFormModal loading={saving} zones={zones} onClose={() => setOpen(false)} onSubmit={create} /> : null}
    </div>
  );
}
