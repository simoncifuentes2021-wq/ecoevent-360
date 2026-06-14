"use client";

import { Upload } from "lucide-react";
import type { DragEvent } from "react";

import { CameraFilePicker } from "@/components/files/CameraFilePicker";

export function FileDropzone({ onFile }: { onFile: (file: File) => void }) {
  function drop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) onFile(file);
  }

  return (
    <div
      className="flex cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed border-emerald-200 bg-emerald-50/40 p-8 text-center transition hover:bg-emerald-50"
      onDragOver={(event) => event.preventDefault()}
      onDrop={drop}
    >
      <Upload className="h-9 w-9 text-emerald-700" />
      <span className="mt-3 text-sm font-semibold text-slate-950">Arrastra un archivo o selecciona desde tu equipo</span>
      <span className="mt-1 text-xs text-slate-500">JPG, PNG, WEBP o PDF hasta 10MB</span>
      <div className="mt-4 w-full max-w-md">
        <CameraFilePicker onFile={onFile} />
      </div>
    </div>
  );
}
