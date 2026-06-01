"use client";

import { Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import { downloadQrCode } from "@/lib/api/qr";
import type { QrCode } from "@/types/qr";

export function QrDownloadButton({ qr }: { qr: QrCode }) {
  async function download() {
    const response = await downloadQrCode(qr.id);
    const url = response.url || response.file_url || qr.file_url || qr.image_url;
    if (url) window.open(url, "_blank");
  }

  return <Button onClick={download} size="sm" type="button" variant="secondary"><Download className="h-4 w-4" />Descargar</Button>;
}
