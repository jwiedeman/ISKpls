import { useEffect, useState } from 'react';
import { getStatus, runJob, type StatusResp } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';

interface JobRec {
  name: string;
  ts_utc: string;
  ok: boolean;
}

export default function Dashboard() {
  const [jobs, setJobs] = useState<JobRec[]>([]);
  const [esi, setEsi] = useState<StatusResp['esi'] | null>(null);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const data = await getStatus();
      setJobs(data.jobs || []);
      setEsi(data.esi);
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
        <p>ESI Error Limit: {esi.error_limit_remain} (reset {esi.error_limit_reset}s)</p>
      )}
      <button disabled={loading} onClick={() => run('scheduler_tick')}>Run Scheduler</button>
      <button disabled={loading} onClick={() => run('recommendations')}>Build Recommendations</button>
      <h3>Recent Jobs</h3>
      <ul>
        {jobs.map(j => (
          <li key={j.name + j.ts_utc}>{j.name} @ {j.ts_utc} - {j.ok ? 'OK' : 'Fail'}</li>
        ))}
      </ul>
    </div>
  );
}
