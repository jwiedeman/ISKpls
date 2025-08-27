export const API_BASE = 'http://localhost:8000';

export async function getStatus() {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error('Failed to fetch status');
  return res.json();
}

export async function getSettings() {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error('Failed to fetch settings');
  return res.json();
}

export async function updateSettings(settings: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to update settings');
  return res.json();
}

export async function runJob(name: string) {
  const res = await fetch(`${API_BASE}/jobs/${name}/run`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run job');
  return res.json();
}

export async function getRecommendations(limit = 50, minNet = 0, minMom = 0) {
  const params = new URLSearchParams({
    limit: String(limit),
    min_net: String(minNet),
    min_mom: String(minMom),
  });
  const res = await fetch(`${API_BASE}/recommendations?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch recommendations');
  return res.json();
}
