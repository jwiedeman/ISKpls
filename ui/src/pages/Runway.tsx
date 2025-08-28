import { useEffect, useState } from 'react';
import { API_BASE, getStatus, type StatusSnapshot } from '../api';
import ErrorBanner from '../ErrorBanner';
import Spinner from '../Spinner';

interface EventLog {
  type: string;
  [key: string]: unknown;
}

export default function Runway() {
  const [status, setStatus] = useState<StatusSnapshot | null>(null);
  const [events, setEvents] = useState<EventLog[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    getStatus().then(setStatus).catch(e => setError(String(e)));
    const wsUrl = API_BASE.replace(/^http/, 'ws') + '/ws';
    const ws = new WebSocket(wsUrl);
    ws.onmessage = ev => {
      try {
        const data = JSON.parse(ev.data);
        setEvents(prev => [...prev.slice(-99), data]);
        if (data.type === 'counts' && data.counts) {
          setStatus(s => ({ ...(s || {}), counts: data.counts }));
        }
        if (data.type === 'esi') {
          setStatus(s => ({ ...(s || {}), esi: { remain: data.remain, reset: data.reset } }));
        }
        if (data.type === 'queue') {
          setStatus(s => ({ ...(s || {}), queue: data.depth }));
        }
      } catch {
        // ignore
      }
    };
    ws.onerror = () => setError('WebSocket error');
    return () => ws.close();
  }, []);

  if (!status && !error) return <Spinner />;

  const counts = status?.counts || {};
  return (
    <div>
      <h2>Runway</h2>
      <ErrorBanner message={error} />
      <div>Types last 10m: {counts['types_10m'] ?? 0}</div>
      <div>Types last 1h: {counts['types_1h'] ?? 0}</div>
      <div>ESI Remaining: {status?.esi?.remain ?? ''}</div>
      <div>Queue: {JSON.stringify(status?.queue || {})}</div>
      <h3>Events</h3>
      <ul style={{ maxHeight: '200px', overflowY: 'auto' }}>
        {events.map((e, i) => (
          <li key={i}>{e.type}</li>
        ))}
      </ul>
    </div>
  );
}
