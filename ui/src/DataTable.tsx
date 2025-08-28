import { useReactTable, type ColumnDef, type SortingState, type OnChangeFn, getCoreRowModel, getSortedRowModel, flexRender } from '@tanstack/react-table';

interface Props<T> {
  columns: ColumnDef<T, unknown>[];
  data: T[];
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
  stickyHeader?: boolean;
}

export default function DataTable<T>({ columns, data, sorting, onSortingChange, stickyHeader = false }: Props<T>) {
  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualSorting: true,
  });

  return (
    <div>
      <div style={{ marginBottom: '0.5em' }}>
        {table
          .getAllLeafColumns()
          .filter((col) => col.getCanHide())
          .map((col) => (
            <label key={col.id} style={{ marginRight: '1em' }}>
              <input
                type="checkbox"
                checked={col.getIsVisible()}
                onChange={col.getToggleVisibilityHandler()}
              />{' '}
              {col.id}
            </label>
          ))}
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table>
          <thead style={stickyHeader ? { position: 'sticky', top: 0, background: '#fff' } : undefined}>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th key={header.id} onClick={header.column.getToggleSortingHandler?.()}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
