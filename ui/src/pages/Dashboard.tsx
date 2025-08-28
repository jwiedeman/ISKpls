import { useEffect, useState } from 'react';
import {
  runJob,
  getWatchlist,
  getCoverage,
  type Coverage,
  buildRecommendations,
} from '../api';
import { useEventStream } from '../useEventStream';
import RunwayPanel from '../RunwayPanel';
import { useRunwayVM } from '../runwayVM';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';
import TypeName from '../TypeName';

export default function Dashboard() {
  const { connected, events } = useEventStream();
  const { inflightList, pending } = useRunwayVM(events);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [watchlist, setWatchlist] = useState<number[]>([]);
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  async function refresh() {
    setLoading(true);
    try {
      const wl = await getWatchlist();
      const ids: number[] = (wl.items || []).map((i: { type_id: number }) => i.type_id);
      setWatchlist(ids);
      const cov = await getCoverage();
      setCoverage(cov);
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

  async function run(name: string) {
    setLoading(true);
    try {
      await runJob(name);
      await refresh();
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

  async function buildRecs() {
    setLoading(true);
    try {
      await buildRecommendations();
      await refresh();
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

  const recRunning = inflightList.some((j) => j.job === 'recommendations');
  const recPending = pending.some((p) => p.job === 'recommendations');

  return (
    <div>
      <h2>Dashboard</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      <RunwayPanel connected={connected} events={events} />
      {coverage && (
        <p>
          Types indexed: {coverage.types_indexed} · Books 10m: {coverage.books_10m} ·
          Median age: {coverage.median_age_s}s · 24h types: {coverage.distinct_types_24h}
        </p>
      )}
      <button disabled={loading} onClick={() => run('scheduler_tick')}>Run Scheduler</button>
      <button disabled={loading || recRunning || recPending} onClick={buildRecs}>Build Recommendations</button>
      {recPending && <span style={{ marginLeft: '0.5em' }}>In queue</span>}

      <h3>Watchlist</h3>
      <ul>
        {watchlist.map(id => (
          <li key={id}><TypeName id={id} /></li>
        ))}
      </ul>
    </div>
  );
}
