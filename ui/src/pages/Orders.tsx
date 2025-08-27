import { useEffect, useState } from 'react';
import { getOpenOrders, getOrderHistory, getTypeNames } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';

interface Order {
  order_id: number;
  is_buy: boolean;
  type_id: number;
  price: number;
  volume_total: number;
  volume_remain: number;
  fill_pct: number;
  issued: string;
  escrow: number;
  state?: string;
}

export default function Orders() {
  const [openOrders, setOpenOrders] = useState<Order[]>([]);
  const [history, setHistory] = useState<Order[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [typeNames, setTypeNames] = useState<Record<number, string>>({});

  async function refresh() {
    setLoading(true);
    try {
      const open = await getOpenOrders();
      const hist = await getOrderHistory();
      const openList = open.orders || [];
      const histList = hist.orders || [];
      setOpenOrders(openList);
      setHistory(histList);
      const ids = Array.from(new Set([...openList, ...histList].map((o: Order) => o.type_id)));
      if (ids.length) {
        const names = await getTypeNames(ids);
        setTypeNames(names);
      }
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
      <h2>Orders</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      <button onClick={refresh} disabled={loading}>Refresh</button>

      <h3>Open Orders</h3>
      <table>
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Item</th>
            <th>Price</th>
            <th>Filled %</th>
            <th>Escrow</th>
          </tr>
        </thead>
        <tbody>
          {openOrders.map(o => (
            <tr key={o.order_id}>
              <td>{o.order_id}</td>
              <td>{typeNames[o.type_id] || o.type_id}</td>
              <td>{o.price.toFixed(2)}</td>
              <td>{(o.fill_pct * 100).toFixed(1)}</td>
              <td>{o.escrow.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Recent History</h3>
      <table>
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Item</th>
            <th>Price</th>
            <th>Filled %</th>
            <th>State</th>
          </tr>
        </thead>
        <tbody>
          {history.map(o => (
            <tr key={o.order_id}>
              <td>{o.order_id}</td>
              <td>{typeNames[o.type_id] || o.type_id}</td>
              <td>{o.price.toFixed(2)}</td>
              <td>{(o.fill_pct * 100).toFixed(1)}</td>
              <td>{o.state}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
