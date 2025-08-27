import { useEffect, useState } from 'react';
import { getSettings, updateSettings, getSchedulers, updateSchedulers } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';

interface FieldMeta {
  label: string;
  type: 'number' | 'text';
  min?: number;
  max?: number;
  help?: string;
}

const FIELDS: Record<string, FieldMeta> = {
  STATION_ID: { label: 'Station ID', type: 'number', min: 1, help: 'Default station for valuations' },
  REGION_ID: { label: 'Region ID', type: 'number', min: 1, help: 'Default region for valuations' },
  DATASOURCE: { label: 'Datasource', type: 'text', help: 'EVE data source' },
  VENUE: { label: 'Venue', type: 'text', help: 'Trading venue' },
  SALES_TAX: { label: 'Sales Tax', type: 'number', min: 0, max: 1, help: '0.05 for 5% sales tax' },
  BROKER_BUY: { label: 'Broker Fee (Buy)', type: 'number', min: 0, max: 1 },
  BROKER_SELL: { label: 'Broker Fee (Sell)', type: 'number', min: 0, max: 1 },
  RELIST_HAIRCUT: { label: 'Relist Haircut', type: 'number', min: 0, max: 1 },
  MOM_THRESHOLD: { label: 'MoM Threshold', type: 'number', min: 0, max: 1 },
  MIN_DAYS_TRADED: { label: 'Min Days Traded', type: 'number', min: 0 },
  MIN_DAILY_VOL: { label: 'Min Daily Volume', type: 'number', min: 0 },
  SPREAD_BUFFER: { label: 'Spread Buffer', type: 'number', min: 0, max: 1 },
};

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [schedulers, setSchedulers] = useState<Record<string, { enabled: boolean; interval: number }>>({});
  async function refresh() {
    setLoading(true);
    try {
      const data = await getSettings();
      const subset: Record<string, unknown> = {};
      for (const key of Object.keys(FIELDS)) {
        subset[key] = data[key];
      }
      setSettings(subset);
      const sched = await getSchedulers();
      setSchedulers(sched);
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
    const meta = FIELDS[key];
    let v: unknown = value;
    if (meta.type === 'number') {
      v = value === '' ? '' : Number(value);
    }
    setSettings(s => ({ ...s, [key]: v }));
  }

  async function save() {
    const payload: Record<string, unknown> = {};
    for (const [key, meta] of Object.entries(FIELDS)) {
      const raw = settings[key];
      let val = raw;
      if (meta.type === 'number') {
        val = Number(raw);
        if (isNaN(val as number)) {
          setError(`${meta.label} must be a number`);
          return;
        }
      }
      if (typeof meta.min === 'number' && (val as number) < meta.min) {
        setError(`${meta.label} must be >= ${meta.min}`);
        return;
      }
      if (typeof meta.max === 'number' && (val as number) > meta.max) {
        setError(`${meta.label} must be <= ${meta.max}`);
        return;
      }
      payload[key] = val;
    }
    setLoading(true);
    try {
      await updateSettings(payload);
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

  async function saveSchedulers() {
    setLoading(true);
    try {
      await updateSchedulers(schedulers);
      alert('Saved schedulers');
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
      <form
        onSubmit={e => {
          e.preventDefault();
          save();
        }}
      >
        {Object.entries(FIELDS).map(([k, meta]) => (
          <div key={k} style={{ marginBottom: '0.5em' }}>
            <label>
              {meta.label}:{' '}
              <input
                type={meta.type === 'number' ? 'number' : 'text'}
                min={meta.min}
                max={meta.max}
                step="0.01"
                value={settings[k] as number | string}
                onChange={e => handleChange(k, e.target.value)}
              />
            </label>
            {meta.help && (
              <div>
                <small>{meta.help}</small>
              </div>
            )}
          </div>
        ))}
        <button type="submit" disabled={loading}>Save</button>
      </form>

      <h3>Schedulers</h3>
      {Object.entries(schedulers).map(([name, cfg]) => (
        <div key={name} style={{ marginBottom: '0.5em' }}>
          <label>
            <input
              type="checkbox"
              checked={cfg.enabled}
              onChange={e =>
                setSchedulers(s => ({ ...s, [name]: { ...cfg, enabled: e.target.checked } }))
              }
            />
            {` ${name}`}
          </label>
          <input
            type="number"
            value={cfg.interval}
            style={{ marginLeft: '0.5em' }}
            onChange={e =>
              setSchedulers(s => ({ ...s, [name]: { ...cfg, interval: Number(e.target.value) } }))
            }
          />
        </div>
      ))}
      <button onClick={saveSchedulers} disabled={loading}>Save Schedulers</button>
    </div>
  );
}
