"use client";

import { Camera, Upload } from "lucide-react";
import type { ChangeEvent } from "react";

const imageAccept = "image/jpeg,image/png,image/webp";
const fileAccept = "image/jpeg,image/png,image/webp,application/pdf";
const baseClass =
  "inline-flex h-10 w-full cursor-pointer items-center justify-center gap-2 rounded-md px-4 text-sm font-semibold transition focus-within:ring-2 focus-within:ring-primary/30";

export function CameraFilePicker({
  disabled,
  onFile
}: {
  disabled?: boolean;
  onFile: (file: File) => void;
}) {
  function pick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) onFile(file);
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <label className={`${baseClass} bg-primary text-primary-foreground hover:bg-primary/90 ${disabled ? "cursor-not-allowed opacity-60" : ""}`}>
        <input
          accept={imageAccept}
          capture="environment"
          className="hidden"
          disabled={disabled}
          type="file"
          onChange={pick}
        />
        <Camera className="h-4 w-4" />
        Tomar foto
      </label>
      <label className={`${baseClass} bg-white text-foreground shadow-sm hover:bg-muted ${disabled ? "cursor-not-allowed opacity-60" : ""}`}>
        <input
          accept={fileAccept}
          className="hidden"
          disabled={disabled}
          type="file"
          onChange={pick}
        />
        <Upload className="h-4 w-4" />
        Seleccionar archivo
      </label>
    </div>
  );
}
