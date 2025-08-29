import { useEffect, useState } from 'react';
import { getDbItems, type DbItem, getSettings } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';
import { type ColumnDef, type SortingState } from '@tanstack/react-table';
import TypeName from '../TypeName';
import StalenessBadge from '../StalenessBadge';
import DataTable from '../DataTable';

const columns: ColumnDef<DbItem>[] = [
  {
    accessorKey: 'type_name',
    header: 'Item',
    cell: ({ row }) => (
      <TypeName id={row.original.type_id} name={row.original.type_name} />
    ),
  },
  { accessorKey: 'best_bid', header: 'Best Bid', meta: { numeric: true } },
  { accessorKey: 'best_ask', header: 'Best Ask', meta: { numeric: true } },
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
    header: 'Staleness',
    cell: (info) => <StalenessBadge ms={info.getValue<number>() ?? 0} />,
  },
  { accessorKey: 'last_updated', header: 'Updated' },
];

export default function Db() {
  const [rows, setRows] = useState<DbItem[]>([]);
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'last_updated', desc: true },
  ]);
  const [search, setSearch] = useState('');
  const [minProfit, setMinProfit] = useState(0);
  const [dealFilters, setDealFilters] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fees, setFees] = useState<{ buy: number; sell: number } | null>(null);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const PAGE_SIZE = 25;

  async function refresh() {
    setLoading(true);
    try {
      const sort = sorting[0]?.id ?? 'last_updated';
      const dir = sorting[0]?.desc ? 'desc' : 'asc';
      const data = await getDbItems({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        sort,
        dir,
        search,
        min_profit_pct: minProfit,
        deal: dealFilters,
      });
      setRows(data.rows || []);
       setTotal(data.total || 0);
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
  }, [sorting, search, minProfit, dealFilters, page]);

  useEffect(() => {
    setPage(0);
  }, [sorting, search, minProfit, dealFilters]);

  useEffect(() => {
    (async () => {
      try {
        const s = await getSettings();
        setFees({
          buy: s.BROKER_BUY,
          sell: s.SALES_TAX + s.BROKER_SELL + s.RELIST_HAIRCUT,
        });
      } catch {
        // ignore
      }
    })();
  }, []);

  function toggleDeal(d: string) {
    setDealFilters((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]
    );
  }

  function exportCsv() {
    if (!rows.length) return;
    const headers = [
      'type_id',
      'type_name',
      'best_bid',
      'best_ask',
      'profit_pct',
      'profit_isk',
      'deal',
      'last_updated',
      'mom',
      'est_daily_vol',
    ];
    const csvRows = rows.map((r) => [
      r.type_id,
      r.type_name,
      r.best_bid ?? '',
      r.best_ask ?? '',
      r.profit_pct,
      r.profit_isk,
      r.deal,
      r.last_updated,
      r.mom ?? '',
      r.est_daily_vol ?? '',
    ]);
    const csv = [headers.join(','), ...csvRows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'db_items.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <h2>DB</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      <div>
        <label>
          Search:{' '}
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="name or id"
          />
        </label>
        <label style={{ marginLeft: '1em' }}>
          Min Profit %:{' '}
          <input
            type="number"
            value={minProfit}
            onChange={(e) => setMinProfit(Number(e.target.value))}
          />
        </label>
        <span style={{ marginLeft: '1em' }}>
          Deal:
          {['Great', 'Good', 'Neutral', 'Bad'].map((d) => (
            <label key={d} style={{ marginLeft: '0.5em' }}>
              <input
                type="checkbox"
                checked={dealFilters.includes(d)}
                onChange={() => toggleDeal(d)}
              />{' '}
              {d}
            </label>
          ))}
        </span>
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
        {fees && (
          <span
            style={{ marginLeft: '0.5em', border: '1px solid #ccc', padding: '2px 4px' }}
          >
            Fees: buy {(fees.buy * 100).toFixed(2)}% sell {(fees.sell * 100).toFixed(2)}%
          </span>
        )}
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
      </div>
      <DataTable
        columns={columns}
        data={rows}
        sorting={sorting}
        onSortingChange={setSorting}
        pageIndex={page}
        pageCount={Math.ceil(total / PAGE_SIZE)}
        onPageChange={(updater) => {
          const next =
            typeof updater === 'function'
              ? updater({ pageIndex: page, pageSize: PAGE_SIZE })
              : updater;
          setPage(next.pageIndex);
        }}
        stickyHeader
      />
    </div>
  );
}

