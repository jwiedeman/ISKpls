import { useEffect, useState } from 'react';
import { getPortfolioNav } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';

interface Snapshot {
  wallet_balance: number;
  buy_escrow: number;
  sell_gross: number;
  inventory_quicksell: number;
  inventory_mark: number;
  nav_quicksell: number;
  nav_mark: number;
}

export default function Portfolio() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const data = await getPortfolioNav();
      setSnap(data);
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

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div>
      <h2>Portfolio</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      <button onClick={refresh} disabled={loading}>Refresh</button>
      {snap && (
        <table>
          <tbody>
            <tr><td>Wallet Balance</td><td>{snap.wallet_balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td></tr>
            <tr><td>Buy Escrow</td><td>{snap.buy_escrow.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td></tr>
            <tr><td>Sell Gross</td><td>{snap.sell_gross.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td></tr>
            <tr><td>Inventory (Quicksell)</td><td>{snap.inventory_quicksell.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td></tr>
            <tr><td>Inventory (Mark)</td><td>{snap.inventory_mark.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td></tr>
            <tr><td>NAV (Quicksell)</td><td>{snap.nav_quicksell.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td></tr>
            <tr><td>NAV (Mark)</td><td>{snap.nav_mark.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td></tr>
          </tbody>
        </table>
      )}
    </div>
  );
}
