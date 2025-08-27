import { useEffect, useState } from 'react';
import { getSettings, updateSettings } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function refresh() {
    setLoading(true);
    try {
      const data = await getSettings();
      setSettings(data);
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

  function handleChange(key: string, value: string) {
    setSettings(s => ({ ...s, [key]: value }));
  }

  async function save() {
    setLoading(true);
    try {
      await updateSettings(settings);
      alert('Saved');
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

  return (
    <div>
      <h2>Settings</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      <form onSubmit={e => { e.preventDefault(); save(); }}>
        {Object.entries(settings).map(([k, v]) => (
          <div key={k}>
            <label>
              {k}: <input value={String(v)} onChange={e => handleChange(k, e.target.value)} />
            </label>
          </div>
        ))}
        <button type="submit" disabled={loading}>Save</button>
      </form>
    </div>
  );
}
