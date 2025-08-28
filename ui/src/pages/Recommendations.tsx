import { useEffect, useState } from 'react';
import { getRecommendations, getWatchlist, addWatchlist, removeWatchlist } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';
import TypeName from '../TypeName';

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

export default function Recommendations() {
  const [recs, setRecs] = useState<Rec[]>([]);
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
      const data = await getRecommendations(50, minNet, minMom, search);
      setRecs(data.results || []);
      const wl = await getWatchlist();
      setWatchlist(new Set((wl.items || []).map((i: { type_id: number }) => i.type_id)));
      setError('');
    } catch (e: unknown) {
      if (e instanceof Error) {
        setError(e.message);
      } else {
        setError(String(e));
      }
    } finally {
      setLoading(false);
    }
  }

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
      // ignore errors
    }
  }

  function exportCsv() {
    if (!recs.length) return;
    const headers = [
      'type_id',
      'type_name',
      'net_pct',
      'uplift_mom',
      'daily_capacity',
      'best_bid',
      'best_ask',
      'daily_volume',
      'ts_utc',
    ];
    const rows = recs.map(r => [
      r.type_id,
      r.type_name,
      r.net_pct,
      r.uplift_mom,
      r.daily_capacity,
      r.best_bid ?? '',
      r.best_ask ?? '',
      r.daily_volume ?? '',
      r.ts_utc,
    ]);
    const csv = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'recommendations.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="name or id"
          />
        </label>
        <button style={{ marginLeft: '1em' }} onClick={refresh} disabled={loading}>Refresh</button>
        <button
          style={{ marginLeft: '1em' }}
          onClick={exportCsv}
          disabled={!recs.length}
        >
          Export CSV
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>★</th>
            <th>Item</th>
            <th>Net %</th>
            <th>MoM %</th>
            <th>Daily ISK</th>
            <th>Bid</th>
            <th>Ask</th>
            <th>Volume</th>
            <th>Explain</th>
          </tr>
        </thead>
        <tbody>
          {recs.map(r => (
            <tr key={r.type_id}>
              <td>
                <button
                  onClick={() => toggleWatchlist(r.type_id)}
                  disabled={loading}
                >
                  {watchlist.has(r.type_id) ? '★' : '☆'}
                </button>
              </td>
              <td><TypeName id={r.type_id} name={r.type_name} /></td>
              <td>{(r.net_pct * 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>{(r.uplift_mom * 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>{Math.round(r.daily_capacity).toLocaleString()}</td>
              <td>{(r.best_bid ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>{(r.best_ask ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>{(r.daily_volume ?? 0).toLocaleString()}</td>
              <td>
                <button onClick={() => setSelected(r)}>Explain</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

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
