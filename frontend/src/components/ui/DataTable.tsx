import React from "react";

interface Column<T> {
  header: string;
  accessorKey: keyof T | string;
  cell?: (item: T) => React.ReactNode;
  align?: "left" | "right" | "center";
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyExtractor: (item: T, index: number) => string;
  emptyMessage?: string;
}

export function DataTable<T>({ data, columns, keyExtractor, emptyMessage = "No data available" }: DataTableProps<T>) {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-32 flex items-center justify-center text-[var(--color-dim)] text-sm border border-[var(--color-hairline)] bg-[var(--color-panel)]">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto border border-[var(--color-hairline)] bg-[var(--color-panel)]">
      <table className="w-full text-sm">
        <thead className="bg-[var(--color-elevated)] sticky top-0">
          <tr>
            {columns.map((col, i) => (
              <th 
                key={i} 
                className={`py-2 px-4 text-${col.align || 'left'} font-medium text-[var(--color-muted)] border-b border-[var(--color-hairline)] whitespace-nowrap`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-hairline)]">
          {data.map((item, i) => (
            <tr key={keyExtractor(item, i)} className="hover:bg-[var(--color-elevated)] transition-colors">
              {columns.map((col, j) => (
                <td 
                  key={j} 
                  className={`py-1.5 px-4 text-${col.align || 'left'} whitespace-nowrap text-[var(--color-primary)]`}
                >
                  {col.cell ? col.cell(item) : (item as any)[col.accessorKey]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
