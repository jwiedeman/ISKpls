import { useEffect, useState } from 'react';
import { getRecommendations, getWatchlist, addWatchlist, removeWatchlist } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';
import TypeName from '../TypeName';
import {
  useReactTable,
  type ColumnDef,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
} from '@tanstack/react-table';

interface Rec {
  type_id: number;
  type_name: string;
  ts_utc: string;
  net_pct: number;
  uplift_mom: number;
  daily_capacity: number;
  best_bid: number | null;
  best_ask: number | null;
  daily_volume: number | null;
  details: Record<string, unknown>;
}

const columns: ColumnDef<Rec>[] = [
  {
    accessorKey: 'type_name',
    header: 'Item',
    cell: ({ row }) => `${row.original.type_name} · #${row.original.type_id}`,
  },
  { accessorKey: 'uplift_mom', header: 'MoM %', meta: { numeric: true },
    cell: info => (info.getValue<number>() * 100).toFixed(2) },
  { accessorKey: 'net_pct', header: 'Net %', meta: { numeric: true },
    cell: info => (info.getValue<number>() * 100).toFixed(2) },
  { accessorKey: 'best_bid', header: 'Best Bid', meta: { numeric: true } },
  { accessorKey: 'best_ask', header: 'Best Ask', meta: { numeric: true } },
  { accessorKey: 'daily_volume', header: 'Daily Vol', meta: { numeric: true } },
  { accessorKey: 'ts_utc', header: 'Updated' },
];

export default function Recommendations() {
  const [rows, setRows] = useState<Rec[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [sorting, setSorting] = useState<SortingState>([{ id: 'net_pct', desc: true }]);
  const [minNet, setMinNet] = useState(0);
  const [minMom, setMinMom] = useState(0);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Rec | null>(null);
  const [watchlist, setWatchlist] = useState<Set<number>>(new Set());

  async function refresh() {
    setLoading(true);
    try {
      const sort = sorting[0]?.id ?? 'net_pct';
      const dir = sorting[0]?.desc ? 'desc' : 'asc';
      const data = await getRecommendations({
        limit: 50,
        offset: page * 50,
        sort,
        dir,
        search,
        min_net: minNet,
        min_mom: minMom,
      });
      setRows(data.rows || []);
      setTotal(data.total || 0);
      const wl = await getWatchlist();
      setWatchlist(new Set((wl.items || []).map((i: { type_id: number }) => i.type_id)));
      setError('');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, sorting, search]);

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualSorting: true,
  });

  async function toggleWatchlist(id: number) {
    try {
      if (watchlist.has(id)) {
        await removeWatchlist(id);
        setWatchlist(prev => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      } else {
        await addWatchlist(id);
        setWatchlist(prev => new Set(prev).add(id));
      }
    } catch {
      // ignore
    }
  }

  function exportCsv() {
    if (!rows.length) return;
    const headers = ['type_id','type_name','net_pct','uplift_mom','daily_capacity','best_bid','best_ask','daily_volume','ts_utc'];
    const csvRows = rows.map(r => [r.type_id,r.type_name,r.net_pct,r.uplift_mom,r.daily_capacity,r.best_bid ?? '',r.best_ask ?? '',r.daily_volume ?? '',r.ts_utc]);
    const csv = [headers.join(','), ...csvRows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'recommendations.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <h2>Recommendations</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      <div>
        <label>
          Min Net %: <input type="number" value={minNet} onChange={e => setMinNet(Number(e.target.value))} />
        </label>
        <label style={{ marginLeft: '1em' }}>
          Min MoM %: <input type="number" value={minMom} onChange={e => setMinMom(Number(e.target.value))} />
        </label>
        <label style={{ marginLeft: '1em' }}>
          Search:{' '}
          <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="name or id" />
        </label>
        <button style={{ marginLeft: '1em' }} onClick={refresh} disabled={loading}>Refresh</button>
        <button style={{ marginLeft: '1em' }} onClick={exportCsv} disabled={!rows.length}>Export CSV</button>
      </div>
      <table>
        <thead>
          {table.getHeaderGroups().map(hg => (
            <tr key={hg.id}>
              <th>★</th>
              {hg.headers.map(header => (
                <th key={header.id} onClick={header.column.getToggleSortingHandler?.()}>
                  {header.isPlaceholder ? null : header.column.columnDef.header as string}
                </th>
              ))}
              <th>Explain</th>
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map(row => (
            <tr key={row.original.type_id}>
              <td>
                <button onClick={() => toggleWatchlist(row.original.type_id)} disabled={loading}>
                  {watchlist.has(row.original.type_id) ? '★' : '☆'}
                </button>
              </td>
              {row.getVisibleCells().map(cell => (
                <td key={cell.id}>{cell.renderCell()}</td>
              ))}
              <td><button onClick={() => setSelected(row.original)}>Explain</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: '1em' }}>
        <button disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>Prev</button>
        <span style={{ margin: '0 1em' }}>
          Page {page + 1} / {Math.max(1, Math.ceil(total / 50))}
        </span>
        <button disabled={(page + 1) * 50 >= total} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>

      {selected && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div style={{ background: '#fff', padding: '1em', maxWidth: '400px' }}>
            <h3><TypeName id={selected.type_id} name={selected.type_name} /></h3>
            <pre>{JSON.stringify(selected.details, null, 2)}</pre>
            <button onClick={() => setSelected(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
