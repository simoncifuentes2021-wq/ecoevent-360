"use client";

import { Upload } from "lucide-react";
import type { ChangeEvent, DragEvent } from "react";

const accept = "image/jpeg,image/png,application/pdf";

export function FileDropzone({ onFile }: { onFile: (file: File) => void }) {
  function pick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onFile(file);
  }

  function drop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) onFile(file);
  }

  return (
    <label
      className="flex cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed border-emerald-200 bg-emerald-50/40 p-8 text-center transition hover:bg-emerald-50"
      onDragOver={(event) => event.preventDefault()}
      onDrop={drop}
    >
      <Upload className="h-9 w-9 text-emerald-700" />
      <span className="mt-3 text-sm font-semibold text-slate-950">Arrastra un archivo o selecciona desde tu equipo</span>
      <span className="mt-1 text-xs text-slate-500">JPG, PNG o PDF hasta 10MB</span>
      <input accept={accept} className="hidden" type="file" onChange={pick} />
    </label>
  );
}
