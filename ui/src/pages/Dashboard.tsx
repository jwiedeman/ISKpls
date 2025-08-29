import { useEffect, useState } from 'react';
import {
  runJob,
  getWatchlist,
  getCoverage,
  type Coverage,
  buildRecommendations,
  getSchedulers,
  updateSchedulers,
  getStatus,
  type StatusSnapshot,
} from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';
import TypeName from '../TypeName';

interface SchedulerCfg {
  enabled: boolean;
  interval: number;
}

export default function Dashboard() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [watchlist, setWatchlist] = useState<number[]>([]);
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [schedulers, setSchedulers] = useState<Record<string, SchedulerCfg>>({});
  const [status, setStatus] = useState<StatusSnapshot | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const wl = await getWatchlist();
      const ids: number[] = (wl.items || []).map((i: { type_id: number }) => i.type_id);
      setWatchlist(ids);
      const cov = await getCoverage();
      setCoverage(cov);
      const sched = await getSchedulers();
      setSchedulers(sched);
      const stat = await getStatus();
      setStatus(stat);
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

  async function runNow(name: string) {
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

  async function toggleScheduler(name: string, enabled: boolean) {
    setLoading(true);
    try {
      const cfg = schedulers[name];
      await updateSchedulers({ [name]: { enabled, interval: cfg.interval } });
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

  return (
    <div>
      <h2>Dashboard</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      {status && (
        <div>
          <p>
            ESI remain: {status.esi?.remain ?? ''} reset: {status.esi?.reset ?? ''}
          </p>
          {status.counts && (
            <p>
              {Object.entries(status.counts).map(([k, v]) => (
                <span key={k} style={{ marginRight: '0.5em' }}>
                  {k}: {v}
                </span>
              ))}
            </p>
          )}
        </div>
      )}
      {coverage && (
        <p>
          Types indexed: {coverage.types_indexed} · Books 10m: {coverage.books_10m} ·
          Median age: {coverage.median_age_s}s · 24h types: {coverage.distinct_types_24h}
        </p>
      )}
      <h3>Schedulers</h3>
      <table>
        <thead>
          <tr>
            <th>Job</th>
            <th>Interval (m)</th>
            <th>Enabled</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(schedulers).map(([name, cfg]) => (
            <tr key={name}>
              <td>{name}</td>
              <td>{cfg.interval}</td>
              <td>{cfg.enabled ? 'Yes' : 'No'}</td>
              <td>
                <button disabled={loading} onClick={() => runNow(name)}>Run now</button>{' '}
                <button
                  disabled={loading}
                  onClick={() => toggleScheduler(name, !cfg.enabled)}
                >
                  {cfg.enabled ? 'Pause' : 'Resume'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button disabled={loading} onClick={buildRecs} style={{ marginTop: '1em' }}>
        Build Recommendations
      </button>
      <h3>Watchlist</h3>
      <ul>
        {watchlist.map((id) => (
          <li key={id}>
            <TypeName id={id} />
          </li>
        ))}
      </ul>
    </div>
  );
}
