import { cn } from '@/lib/utils';

interface DataTableProps {
  data: Record<string, unknown>[];
}

export function DataTable({ data }: DataTableProps) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-muted-foreground">
        No records found
      </div>
    );
  }

  const columns = Object.keys(data[0]);

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-secondary/60">
            {columns.map((column) => (
              <th
                key={column}
                className="px-4 py-3 text-left font-semibold text-foreground whitespace-nowrap border-b border-border"
              >
                {column.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className={cn(
                "transition-colors hover:bg-muted/50",
                rowIndex % 2 === 0 ? "bg-card/30" : "bg-card/10"
              )}
            >
              {columns.map((column) => (
                <td
                  key={column}
                  className="px-4 py-3 text-muted-foreground whitespace-nowrap border-b border-border/50"
                >
                  {formatCellValue(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') {
    return value.toLocaleString();
  }
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (value instanceof Date) return value.toLocaleDateString();
  return String(value);
}
