import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

export function FormActions({
  cancelHref,
  loading,
  submitLabel = "Guardar",
  loadingLabel = "Guardando...",
  extra
}: {
  cancelHref: string;
  loading?: boolean;
  submitLabel?: string;
  loadingLabel?: string;
  extra?: ReactNode;
}) {
  return (
    <div className="flex flex-col-reverse gap-3 border-t pt-5 sm:flex-row sm:items-center sm:justify-between">
      <div>{extra}</div>
      <div className="flex gap-3">
        <Link href={cancelHref}>
          <Button type="button" variant="secondary">
            Cancelar
          </Button>
        </Link>
        <Button disabled={loading} type="submit">
          {loading ? loadingLabel : submitLabel}
        </Button>
      </div>
    </div>
  );
}
