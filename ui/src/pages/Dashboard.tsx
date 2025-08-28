import { useEffect, useState } from 'react';
import { getStatus, runJob, type StatusSnapshot, getWatchlist, getCoverage } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';
import TypeName from '../TypeName';

interface JobRec {
  job: string;
  ts?: string;
  ok: boolean;
  ms?: number;
}

export default function Dashboard() {
  const [jobs, setJobs] = useState<JobRec[]>([]);
  const [esi, setEsi] = useState<StatusSnapshot['esi'] | null>(null);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [watchlist, setWatchlist] = useState<number[]>([]);
  const [coverage, setCoverage] = useState<any>(null);

  async function refresh() {
    setLoading(true);
    try {
      const data = await getStatus();
      setJobs(data.last_runs || []);
      setEsi(data.esi);
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

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div>
      <h2>Dashboard</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      {esi && (
        <p>ESI Error Limit: {esi.remain} (reset {esi.reset}s)</p>
      )}
      {coverage && (
        <p>
          Types indexed: {coverage.types_indexed} · Books 10m: {coverage.books_last_10m} ·
          Median age: {Math.round(coverage.median_snapshot_age_ms / 1000)}s
        </p>
      )}
      <button disabled={loading} onClick={() => run('scheduler_tick')}>Run Scheduler</button>
      <button disabled={loading} onClick={() => run('recommendations')}>Build Recommendations</button>
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
