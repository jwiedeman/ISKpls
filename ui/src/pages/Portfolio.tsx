import { useEffect, useState } from 'react';
import { getPortfolioSummary } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';

interface Summary {
  liquid: number;
  buy_escrow: number;
  sell_value_quicksell: number;
  sell_value_mark: number;
  nav_quicksell: number;
  nav_mark: number;
  realized_7d: number;
  realized_30d: number;
  basis: 'mark' | 'quicksell';
}

export default function Portfolio() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [basis, setBasis] = useState<'mark' | 'quicksell'>('mark');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const data = await getPortfolioSummary(basis);
      setSummary(data);
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
  }, [basis]);

  function format(n: number) {
    return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  return (
    <div>
      <h2>Portfolio</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      <div style={{ marginBottom: '1em' }}>
        <button onClick={() => setBasis('mark')} disabled={basis === 'mark'}>
          Mark
        </button>
        <button onClick={() => setBasis('quicksell')} disabled={basis === 'quicksell'} style={{ marginLeft: '0.5em' }}>
          Quicksell
        </button>
        <button onClick={refresh} disabled={loading} style={{ marginLeft: '1em' }}>
          Refresh
        </button>
      </div>
      {summary && (
        <div style={{ display: 'flex', gap: '1em', flexWrap: 'wrap' }}>
          <div style={{ border: '1px solid #ccc', padding: '0.5em', flex: '1 1 150px' }}>
            <strong>Liquid</strong>
            <div>{format(summary.liquid)}</div>
          </div>
          <div style={{ border: '1px solid #ccc', padding: '0.5em', flex: '1 1 150px' }}>
            <strong>Buy Escrow</strong>
            <div>{format(summary.buy_escrow)}</div>
          </div>
          <div style={{ border: '1px solid #ccc', padding: '0.5em', flex: '1 1 150px' }}>
            <strong>Sell Value</strong>
            <div>{format(basis === 'mark' ? summary.sell_value_mark : summary.sell_value_quicksell)}</div>
          </div>
          <div style={{ border: '1px solid #ccc', padding: '0.5em', flex: '1 1 150px' }}>
            <strong>NAV</strong>
            <div>{format(basis === 'mark' ? summary.nav_mark : summary.nav_quicksell)}</div>
          </div>
        </div>
      )}
    </div>
  );
}
