import { useEffect, useState } from 'react';
import { getStatus, runJob } from '../api';

interface JobRec {
  name: string;
  ts_utc: string;
  ok: boolean;
}

export default function Dashboard() {
  const [jobs, setJobs] = useState<JobRec[]>([]);
  const [error, setError] = useState<string>('');

  async function refresh() {
    try {
      const data = await getStatus();
      setJobs(data.jobs || []);
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
      <h2>Dashboard</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <button onClick={() => { runJob('scheduler_tick').then(refresh); }}>Run Scheduler</button>
      <button onClick={() => { runJob('recommendations').then(refresh); }}>Build Recommendations</button>
      <h3>Recent Jobs</h3>
      <ul>
        {jobs.map(j => (
          <li key={j.name + j.ts_utc}>{j.name} @ {j.ts_utc} - {j.ok ? 'OK' : 'Fail'}</li>
        ))}
      </ul>
    </div>
  );
}
