import { useEffect, useState } from 'react';
import { getRecommendations } from '../api';

interface Rec {
  type_id: number;
  ts_utc: string;
  net_pct: number;
  uplift_mom: number;
  daily_capacity: number;
}

export default function Recommendations() {
  const [recs, setRecs] = useState<Rec[]>([]);
  const [minNet, setMinNet] = useState(0);
  const [minMom, setMinMom] = useState(0);
  const [error, setError] = useState('');

  async function refresh() {
    try {
      const data = await getRecommendations(50, minNet, minMom);
      setRecs(data.results || []);
      setError('');
    } catch (e: unknown) {
      if (e instanceof Error) {
        setError(e.message);
      } else {
        setError(String(e));
      }
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <h2>Recommendations</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <div>
        <label>
          Min Net %: <input type="number" value={minNet} onChange={e => setMinNet(Number(e.target.value))} />
        </label>
        <label style={{ marginLeft: '1em' }}>
          Min MoM %: <input type="number" value={minMom} onChange={e => setMinMom(Number(e.target.value))} />
        </label>
        <button style={{ marginLeft: '1em' }} onClick={refresh}>Refresh</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Type ID</th>
            <th>Net %</th>
            <th>MoM %</th>
            <th>Daily ISK</th>
          </tr>
        </thead>
        <tbody>
          {recs.map(r => (
            <tr key={r.type_id}>
              <td>{r.type_id}</td>
              <td>{(r.net_pct * 100).toFixed(2)}</td>
              <td>{(r.uplift_mom * 100).toFixed(2)}</td>
              <td>{Math.round(r.daily_capacity)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
