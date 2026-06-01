import type { ReactNode } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export type DataTableColumn<T> = {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
};

export function DataTable<T>({
  columns,
  data,
  loading,
  error,
  emptyTitle,
  emptyDescription,
  actions,
  getRowKey,
  page,
  limit,
  total,
  onPageChange
}: {
  columns: DataTableColumn<T>[];
  data: T[];
  loading?: boolean;
  error?: string | null;
  emptyTitle: string;
  emptyDescription?: string;
  actions?: (row: T) => ReactNode;
  getRowKey?: (row: T, index: number) => string;
  page?: number;
  limit?: number;
  total?: number;
  onPageChange?: (page: number) => void;
}) {
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  const totalPages = total && limit ? Math.max(1, Math.ceil(total / limit)) : 1;

  return (
    <Card>
      <CardContent>
        {data.length === 0 ? (
          <EmptyState description={emptyDescription || "No hay registros para mostrar con los filtros actuales."} title={emptyTitle} />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-muted-foreground">
                  <tr className="border-b">
                    {columns.map((column) => (
                      <th className={`py-3 pr-4 ${column.className ?? ""}`} key={column.key}>
                        {column.header}
                      </th>
                    ))}
                    {actions ? <th className="py-3 text-right">Acciones</th> : null}
                  </tr>
                </thead>
                <tbody>
                  {data.map((row, index) => (
                    <tr className="border-b last:border-0" key={getRowKey ? getRowKey(row, index) : index}>
                      {columns.map((column) => (
                        <td className={`py-3 pr-4 align-middle ${column.className ?? ""}`} key={column.key}>
                          {column.cell(row)}
                        </td>
                      ))}
                      {actions ? <td className="py-3 pl-4 align-middle">{actions(row)}</td> : null}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {onPageChange && page && total ? (
              <div className="mt-4 flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-muted-foreground">
                  Página {page} de {totalPages} · {total} registros
                </p>
                <div className="flex gap-2">
                  <Button disabled={page <= 1} onClick={() => onPageChange(page - 1)} type="button" variant="secondary">
                    Anterior
                  </Button>
                  <Button disabled={page >= totalPages} onClick={() => onPageChange(page + 1)} type="button" variant="secondary">
                    Siguiente
                  </Button>
                </div>
              </div>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
