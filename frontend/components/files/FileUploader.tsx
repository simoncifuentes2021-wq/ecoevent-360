"use client";

import { useEffect, useState } from "react";

import { ErrorState } from "@/components/common/ErrorState";
import { FileDropzone } from "@/components/files/FileDropzone";
import { FilePreview } from "@/components/files/FilePreview";
import type { FileUpload } from "@/types/file";

const allowed = ["image/jpeg", "image/png", "application/pdf"];
const maxSize = 10 * 1024 * 1024;

export function FileUploader({ value, onChange }: { value: FileUpload | null; onChange: (value: FileUpload | null) => void }) {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => {
    if (value?.previewUrl) URL.revokeObjectURL(value.previewUrl);
  }, [value?.previewUrl]);

  function select(file: File) {
    setError(null);
    if (!allowed.includes(file.type)) {
      setError("Tipo de archivo no permitido.");
      return;
    }
    if (file.size > maxSize) {
      setError("El archivo supera el tamaño permitido.");
      return;
    }
    onChange({
      file,
      previewUrl: file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined,
      contentType: file.type,
      size: file.size,
      name: file.name
    });
  }

  return (
    <div className="space-y-3">
      {error ? <ErrorState message={error} title="Archivo invalido" /> : null}
      {value ? <FilePreview upload={value} onClear={() => onChange(null)} /> : <FileDropzone onFile={select} />}
    </div>
  );
}
