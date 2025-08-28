import { useEffect, useState } from 'react';
import { getSnipes, type Snipe } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';
import TypeName from '../TypeName';

export default function Snipes() {
  const [snipes, setSnipes] = useState<Snipe[]>([]);
  const [limit, setLimit] = useState(20);
  const [minNet, setMinNet] = useState(0.02);
  const [epsilon, setEpsilon] = useState(0.003);
  const [z, setZ] = useState(2.5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function refresh() {
    setLoading(true);
    try {
      const data = await getSnipes(limit, minNet, epsilon, z);
      setSnipes(data.snipes || []);
      setError('');
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
      else setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <h2>⚡ Snipes</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      <div>
        <label>
          Limit:{' '}
          <input type="number" value={limit} onChange={e => setLimit(Number(e.target.value))} />
        </label>
        <label style={{ marginLeft: '1em' }}>
          Min Net %:{' '}
          <input type="number" value={minNet} step={0.01} onChange={e => setMinNet(Number(e.target.value))} />
        </label>
        <label style={{ marginLeft: '1em' }}>
          Epsilon:{' '}
          <input type="number" value={epsilon} step={0.001} onChange={e => setEpsilon(Number(e.target.value))} />
        </label>
        <label style={{ marginLeft: '1em' }}>
          Z:{' '}
          <input type="number" value={z} step={0.1} onChange={e => setZ(Number(e.target.value))} />
        </label>
        <button style={{ marginLeft: '1em' }} onClick={refresh} disabled={loading}>
          Refresh
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Bid</th>
            <th>Ask</th>
            <th>Units</th>
            <th>Net %</th>
            <th>Net ISK</th>
            <th>Z-score</th>
          </tr>
        </thead>
        <tbody>
          {snipes.map(s => (
            <tr key={s.type_id}>
              <td><TypeName id={s.type_id} name={s.type_name} /></td>
              <td>{s.best_bid.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>{s.best_ask.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>{s.units.toLocaleString()}</td>
              <td>{(s.net_pct * 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>{s.net.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>{s.z_score.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
