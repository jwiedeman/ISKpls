import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getRecommendations,
  getWatchlist,
  addWatchlist,
  removeWatchlist,
  type RecParams,
} from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';
import TypeName from '../TypeName';
import {
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import DataTable from '../DataTable';

interface Rec {
  type_id: number;
  type_name: string;
  best_bid: number | null;
  best_ask: number | null;
  last_updated: string;
  fresh_ms: number;
  profit_pct: number;
  profit_isk: number;
  deal: string;
  mom: number | null;
  est_daily_vol: number | null;
  net_pct: number | null;
  uplift_mom: number | null;
  daily_capacity: number | null;
  details: Record<string, unknown>;
  has_both_sides: boolean;
}

export default function Recommendations() {
  const [rows, setRows] = useState<Rec[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'profit_pct', desc: true },
  ]);
  const [minProfit, setMinProfit] = useState(0);
  const [minMom, setMinMom] = useState(0);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Rec | null>(null);
  const [watchlist, setWatchlist] = useState<Set<number>>(new Set());
  const [showAll, setShowAll] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const sort = sorting[0]?.id ?? 'profit_pct';
      const dir = sorting[0]?.desc ? 'desc' : 'asc';
      const params: RecParams = {
        limit: 50,
        offset: page * 50,
        sort,
        dir,
        search,
        min_profit_pct: minProfit,
        min_mom: minMom,
        show_all: showAll,
        mode: 'profit_only',
      };
      const data = await getRecommendations(params);
      setRows(data.rows || []);
      setTotal(data.total || 0);
      const wl = await getWatchlist();
      setWatchlist(
        new Set((wl.items || []).map((i: { type_id: number }) => i.type_id))
      );
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
  }, [page, sorting, search, showAll, minProfit, minMom]);

  const toggleWatchlist = useCallback(async (id: number) => {
    try {
      if (watchlist.has(id)) {
        await removeWatchlist(id);
        setWatchlist((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      } else {
        await addWatchlist(id);
        setWatchlist((prev) => new Set(prev).add(id));
      }
    } catch {
      // ignore
    }
  }, [watchlist]);

  const columns: ColumnDef<Rec>[] = useMemo(() => [
    {
      id: 'watch',
      header: '★',
      enableHiding: false,
      cell: ({ row }) => (
        <button
          onClick={() => toggleWatchlist(row.original.type_id)}
          disabled={loading}
        >
          {watchlist.has(row.original.type_id) ? '★' : '☆'}
        </button>
      ),
    },
    {
      accessorKey: 'type_name',
      header: 'Item',
      cell: ({ row }) => `${row.original.type_name} · #${row.original.type_id}`,
    },
    {
      accessorKey: 'profit_pct',
      header: 'Profit %',
      meta: { numeric: true },
      cell: ({ row, getValue }) => {
        const val = (getValue<number>() * 100).toFixed(2) + '%';
        return (
          <span style={{ color: row.original.has_both_sides ? undefined : 'gray' }}>
            {val}
          </span>
        );
      },
    },
    {
      accessorKey: 'profit_isk',
      header: 'Profit ISK',
      meta: { numeric: true },
      cell: (info) =>
        (info.getValue<number>() ?? 0).toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }),
    },
    { accessorKey: 'deal', header: 'Deal' },
    { accessorKey: 'best_bid', header: 'Best Bid', meta: { numeric: true } },
    { accessorKey: 'best_ask', header: 'Best Ask', meta: { numeric: true } },
    {
      accessorKey: 'mom',
      header: 'MoM %',
      meta: { numeric: true },
      cell: (info) =>
        info.getValue<number | null>() != null
          ? (info.getValue<number>() * 100).toFixed(2)
          : '',
    },
    {
      accessorKey: 'est_daily_vol',
      header: 'Daily Vol',
      meta: { numeric: true },
    },
    {
      accessorKey: 'fresh_ms',
      header: 'Fresh',
      cell: (info) => {
        const age = info.getValue<number>() ?? 0;
        const color = age < 120000 ? 'green' : age < 600000 ? 'yellow' : 'red';
        return <span style={{ color }}>●</span>;
      },
    },
    { accessorKey: 'last_updated', header: 'Updated' },
    {
      id: 'explain',
      header: 'Explain',
      enableHiding: false,
      cell: ({ row }) => (
        <button onClick={() => setSelected(row.original)}>Explain</button>
      ),
    },
  ], [watchlist, loading, toggleWatchlist]);

  function exportCsv() {
    if (!rows.length) return;
    const headers = [
      'type_id',
      'type_name',
      'profit_pct',
      'profit_isk',
      'deal',
      'best_bid',
      'best_ask',
      'mom',
      'est_daily_vol',
      'last_updated',
    ];
    const csvRows = rows.map((r) => [
      r.type_id,
      r.type_name,
      r.profit_pct,
      r.profit_isk,
      r.deal,
      r.best_bid ?? '',
      r.best_ask ?? '',
      r.mom ?? '',
      r.est_daily_vol ?? '',
      r.last_updated,
    ]);
    const csv = [headers.join(','), ...csvRows.map((r) => r.join(','))].join('\n');
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
          Min Profit %:{' '}
          <input
            type="number"
            value={minProfit}
            onChange={(e) => setMinProfit(Number(e.target.value))}
          />
        </label>
        <label style={{ marginLeft: '1em' }}>
          Min MoM %:{' '}
          <input
            type="number"
            value={minMom}
            onChange={(e) => setMinMom(Number(e.target.value))}
          />
        </label>
        <label style={{ marginLeft: '1em' }}>
          Search:{' '}
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="name or id"
          />
        </label>
        <button
          style={{ marginLeft: '1em' }}
          onClick={refresh}
          disabled={loading}
        >
          Refresh
        </button>
        <button
          style={{ marginLeft: '1em' }}
          onClick={exportCsv}
          disabled={!rows.length}
        >
          Export CSV
        </button>
        <label style={{ marginLeft: '1em' }}>
          <input
            type="checkbox"
            checked={showAll}
            onChange={(e) => setShowAll(e.target.checked)}
          />{' '}
          Show All
        </label>
        {minProfit > 0 && (
          <span
            style={{ marginLeft: '0.5em', border: '1px solid #ccc', padding: '2px 4px' }}
          >
            Profit &gt; {minProfit}%
            <button onClick={() => setMinProfit(0)} style={{ marginLeft: '0.5em' }}>
              ×
            </button>
          </span>
        )}
        {minMom > 0 && (
          <span
            style={{ marginLeft: '0.5em', border: '1px solid #ccc', padding: '2px 4px' }}
          >
            MoM &gt; {minMom}%
            <button onClick={() => setMinMom(0)} style={{ marginLeft: '0.5em' }}>
              ×
            </button>
          </span>
        )}
      </div>
      {rows.length === 0 && !loading ? (
        <div style={{ textAlign: 'center', marginTop: '1em' }}>
          No recommendations found. Try adjusting filters or run the build job.
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={rows}
          sorting={sorting}
          onSortingChange={setSorting}
          stickyHeader
        />
      )}
      <div style={{ marginTop: '1em' }}>
        <button
          disabled={page === 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
        >
          Prev
        </button>
        <span style={{ margin: '0 1em' }}>
          Page {page + 1} / {Math.max(1, Math.ceil(total / 50))}
        </span>
        <button
          disabled={(page + 1) * 50 >= total}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
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
            <h3>
              <TypeName id={selected.type_id} name={selected.type_name} />
            </h3>
            <pre>{JSON.stringify(selected.details, null, 2)}</pre>
            <button onClick={() => setSelected(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

