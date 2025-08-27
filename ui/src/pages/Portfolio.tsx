import { useEffect, useState } from 'react';
import { getPortfolioNav } from '../api';

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

  async function refresh() {
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
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div>
      <h2>Portfolio</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <button onClick={refresh}>Refresh</button>
      {snap && (
        <table>
          <tbody>
            <tr><td>Wallet Balance</td><td>{snap.wallet_balance.toFixed(2)}</td></tr>
            <tr><td>Buy Escrow</td><td>{snap.buy_escrow.toFixed(2)}</td></tr>
            <tr><td>Sell Gross</td><td>{snap.sell_gross.toFixed(2)}</td></tr>
            <tr><td>Inventory (Quicksell)</td><td>{snap.inventory_quicksell.toFixed(2)}</td></tr>
            <tr><td>Inventory (Mark)</td><td>{snap.inventory_mark.toFixed(2)}</td></tr>
            <tr><td>NAV (Quicksell)</td><td>{snap.nav_quicksell.toFixed(2)}</td></tr>
            <tr><td>NAV (Mark)</td><td>{snap.nav_mark.toFixed(2)}</td></tr>
          </tbody>
        </table>
      )}
    </div>
  );
}
