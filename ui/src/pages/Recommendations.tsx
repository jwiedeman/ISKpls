import { useEffect, useState } from 'react';
import { getRecommendations, getTypeNames, getWatchlist, addWatchlist, removeWatchlist } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';

interface Rec {
  type_id: number;
  ts_utc: string;
  net_pct: number;
  uplift_mom: number;
  daily_capacity: number;
  details: Record<string, unknown>;
}

export default function Recommendations() {
  const [recs, setRecs] = useState<Rec[]>([]);
  const [minNet, setMinNet] = useState(0);
  const [minMom, setMinMom] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [typeNames, setTypeNames] = useState<Record<number, string>>({});
  const [selected, setSelected] = useState<Rec | null>(null);
  const [watchlist, setWatchlist] = useState<Set<number>>(new Set());

  async function refresh() {
    setLoading(true);
    try {
      const data = await getRecommendations(50, minNet, minMom);
      setRecs(data.results || []);
      const ids: number[] = Array.from(
        new Set((data.results || []).map((r: Rec) => r.type_id))
      );
      if (ids.length) {
        const names = await getTypeNames(ids);
        setTypeNames(names);
      }
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
        <button style={{ marginLeft: '1em' }} onClick={refresh} disabled={loading}>Refresh</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>★</th>
            <th>Item</th>
            <th>Net %</th>
            <th>MoM %</th>
            <th>Daily ISK</th>
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
              <td>{typeNames[r.type_id] || r.type_id}</td>
              <td>{(r.net_pct * 100).toFixed(2)}</td>
              <td>{(r.uplift_mom * 100).toFixed(2)}</td>
              <td>{Math.round(r.daily_capacity)}</td>
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
            <h3>{typeNames[selected.type_id] || selected.type_id}</h3>
            <pre>{JSON.stringify(selected.details, null, 2)}</pre>
            <button onClick={() => setSelected(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
