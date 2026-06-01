import { Badge } from "@/components/ui/badge";

export type Column<T> = {
  key: keyof T;
  label: string;
  badge?: boolean;
};

export function DataTable<T extends Record<string, string | number>>({
  columns,
  rows
}: {
  columns: Column<T>[];
  rows: T[];
}) {
  return (
    <div className="overflow-hidden rounded-lg border bg-white">
      <table className="w-full min-w-[680px] border-collapse text-left text-sm">
        <thead className="bg-muted text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            {columns.map((column) => (
              <th key={String(column.key)} className="px-4 py-3 font-semibold">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className="border-t">
              {columns.map((column) => (
                <td key={String(column.key)} className="px-4 py-3">
                  {column.badge ? <Badge>{row[column.key]}</Badge> : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

