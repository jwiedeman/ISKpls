import { useEffect, useState } from 'react';
import {
  API_BASE,
  getStatus,
  runJob,
  type StatusSnapshot,
  getWatchlist,
  getCoverage,
  type Coverage,
  buildRecommendations,
} from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';
import TypeName from '../TypeName';

interface JobRec {
  job: string;
  ts?: string;
  ok: boolean;
  ms?: number;
}

interface InflightJob {
  id: number;
  job: string;
  detail?: string;
  progress: number;
}

export default function Dashboard() {
  const [jobs, setJobs] = useState<JobRec[]>([]);
  const [esi, setEsi] = useState<StatusSnapshot['esi'] | null>(null);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [watchlist, setWatchlist] = useState<number[]>([]);
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [inflight, setInflight] = useState<InflightJob[]>([]);
  const [queue, setQueue] = useState<Record<string, number>>({});

  async function refresh() {
    setLoading(true);
    try {
      const data = await getStatus();
      setJobs(data.last_runs || []);
      setEsi(data.esi);
      setInflight((data.inflight as InflightJob[]) || []);
      setQueue(data.queue || {});
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
    const wsUrl = API_BASE.replace('http', 'ws') + '/ws';
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (ev) => {
      try {
        const evt = JSON.parse(ev.data);
        if (evt.type === 'job_started') {
          setInflight((prev) => [...prev, { id: evt.id, job: evt.job, detail: evt.meta?.detail, progress: 0 }]);
        } else if (evt.type === 'job_progress') {
          setInflight((prev) => prev.map((j) => (j.id === evt.id ? { ...j, progress: evt.progress, detail: evt.detail } : j)));
        } else if (evt.type === 'job_finished') {
          setInflight((prev) => prev.filter((j) => j.id !== evt.id));
          setJobs((prev) => [{ job: evt.job, ts: new Date().toISOString(), ok: evt.ok, ms: evt.ms }, ...prev]);
        } else if (evt.type === 'esi') {
          setEsi({ remain: evt.remain, reset: evt.reset });
        } else if (evt.type === 'queue') {
          setQueue(evt.depth || {});
        }
      } catch {
        // ignore malformed events
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div>
      <h2>Dashboard</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      {esi && (<p>ESI Error Limit: {esi.remain} (reset {esi.reset}s)</p>)}
      {inflight.length > 0 && (
        <div>
          <h4>Now Running</h4>
          {inflight.map(j => (
            <div key={j.id}>{j.job} {j.progress ? `${j.progress}%` : ''} {j.detail}</div>
          ))}
        </div>
      )}
      {Object.keys(queue).length > 0 && (
        <p>
          Queue depth: {Object.entries(queue).map(([k,v]) => `${k}:${v}`).join(' · ')}
        </p>
      )}
      {coverage && (
        <p>
          Types indexed: {coverage.types_indexed} · Books 10m: {coverage.books_last_10m} ·
          Median age: {Math.round(coverage.median_snapshot_age_ms / 1000)}s
        </p>
      )}
      <button disabled={loading} onClick={() => run('scheduler_tick')}>Run Scheduler</button>
      <button disabled={loading} onClick={buildRecs}>Build Recommendations</button>
      <h3>Recent Jobs</h3>
      <ul>
        {jobs.map(j => (
          <li key={j.job + (j.ts || '')}>{j.job} @ {j.ts} - {j.ok ? 'OK' : 'Fail'}</li>
        ))}
      </ul>

      <h3>Watchlist</h3>
      <ul>
        {watchlist.map(id => (
          <li key={id}><TypeName id={id} /></li>
        ))}
      </ul>
    </div>
  );
}
