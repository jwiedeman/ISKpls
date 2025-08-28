import { useEffect, useState } from 'react';
import { getOpenOrders, getOrderHistory, getRepriceGuidance } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';
import TypeName from '../TypeName';

interface Order {
  order_id: number;
  is_buy: boolean;
  type_id: number;
  type_name: string;
  price: number;
  volume_total: number;
  volume_remain: number;
  fill_pct: number;
  issued: string;
  escrow: number;
  state?: string;
}

interface Guidance {
  buy_price: number;
  sell_price: number;
  buy_net_pct: number;
  sell_net_pct: number;
}

export default function Orders() {
  const [openOrders, setOpenOrders] = useState<Order[]>([]);
  const [history, setHistory] = useState<Order[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [guidance, setGuidance] = useState<Record<number, Guidance>>({});

  async function refresh() {
    setLoading(true);
    try {
      const open = await getOpenOrders(100, search);
      const hist = await getOrderHistory(100, search);
      const openList = open.orders || [];
      const histList = hist.orders || [];
      setOpenOrders(openList);
      setHistory(histList);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchGuidance(typeId: number) {
    try {
      const g = await getRepriceGuidance(typeId);
      setGuidance(prev => ({ ...prev, [typeId]: g }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div>
      <h2>Orders</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      <div>
        <label>
          Search:{' '}
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="name or id"
          />
        </label>
        <button onClick={refresh} disabled={loading} style={{ marginLeft: '1em' }}>Refresh</button>
      </div>

      <h3>Open Orders</h3>
      <table>
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Item</th>
            <th>Price</th>
            <th>Filled %</th>
            <th>Escrow</th>
            <th>Reprice</th>
          </tr>
        </thead>
        <tbody>
          {openOrders.map(o => (
            <tr key={o.order_id}>
              <td>{o.order_id}</td>
              <td><TypeName id={o.type_id} name={o.type_name} /></td>
              <td>{o.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>{(o.fill_pct * 100).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td>
              <td>{o.escrow.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>
                <button onClick={() => fetchGuidance(o.type_id)} disabled={loading}>±1 tick</button>
                {guidance[o.type_id] && (
                  <div>
                    {o.is_buy
                      ? `${guidance[o.type_id].buy_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${(guidance[o.type_id].buy_net_pct * 100).toFixed(2)}%)`
                      : `${guidance[o.type_id].sell_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${(guidance[o.type_id].sell_net_pct * 100).toFixed(2)}%)`}
                  </div>
                )}
              </td>
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
              <td><TypeName id={o.type_id} name={o.type_name} /></td>
              <td>{o.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td>{(o.fill_pct * 100).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td>
              <td>{o.state}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
