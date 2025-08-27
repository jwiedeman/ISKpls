import { useEffect, useState } from 'react';
import { getSettings, updateSettings } from '../api';

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, any>>({});
  const [error, setError] = useState('');

  useEffect(() => {
    getSettings().then(setSettings).catch(e => setError(e.message));
  }, []);

  function handleChange(key: string, value: string) {
    setSettings(s => ({ ...s, [key]: value }));
  }

  async function save() {
    try {
      await updateSettings(settings);
      alert('Saved');
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div>
      <h2>Settings</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={e => { e.preventDefault(); save(); }}>
        {Object.entries(settings).map(([k, v]) => (
          <div key={k}>
            <label>
              {k}: <input value={String(v)} onChange={e => handleChange(k, e.target.value)} />
            </label>
          </div>
        ))}
        <button type="submit">Save</button>
      </form>
    </div>
  );
}
