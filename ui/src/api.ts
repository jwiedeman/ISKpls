export const API_BASE = 'http://localhost:8000';

export interface StatusResp {
  jobs: { name: string; ts_utc: string; ok: boolean }[];
  esi: { error_limit_remain: number; error_limit_reset: number };
}

export async function getStatus(): Promise<StatusResp> {
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

export async function getRecommendations(limit = 50, minNet = 0, minMom = 0, search = '') {
  const params = new URLSearchParams({
    limit: String(limit),
    min_net: String(minNet),
    min_mom: String(minMom),
  });
  if (search) params.set('search', search);
  const res = await fetch(`${API_BASE}/recommendations?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch recommendations');
  return res.json();
}

export async function getOpenOrders(limit = 100, search = '') {
  const params = new URLSearchParams({ limit: String(limit) });
  if (search) params.set('search', search);
  const res = await fetch(`${API_BASE}/orders/open?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch open orders');
  return res.json();
}

export async function getOrderHistory(limit = 100, search = '') {
  const params = new URLSearchParams({ limit: String(limit) });
  if (search) params.set('search', search);
  const res = await fetch(`${API_BASE}/orders/history?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch order history');
  return res.json();
}

export async function getPortfolioNav() {
  const res = await fetch(`${API_BASE}/portfolio/nav`);
  if (!res.ok) throw new Error('Failed to fetch portfolio NAV');
  return res.json();
}

export async function recomputeValuations() {
  const res = await fetch(`${API_BASE}/valuations/recompute`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to recompute valuations');
  return res.json();
}

export async function getTypeNames(ids: number[]): Promise<Record<number, string>> {
  const params = ids.length ? `?ids=${ids.join(',')}` : '';
  const res = await fetch(`${API_BASE}/types/map${params}`);
  if (!res.ok) throw new Error('Failed to fetch type names');
  const data = await res.json();
  const result: Record<number, string> = {};
  for (const [k, v] of Object.entries(data)) {
    result[Number(k)] = v as string;
  }
  return result;
}

export async function getSchedulers() {
  const res = await fetch(`${API_BASE}/schedulers`);
  if (!res.ok) throw new Error('Failed to fetch schedulers');
  return res.json();
}

export async function updateSchedulers(settings: Record<string, { enabled: boolean; interval: number }>) {
  const res = await fetch(`${API_BASE}/schedulers`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to update schedulers');
  return res.json();
}

export async function getWatchlist() {
  const res = await fetch(`${API_BASE}/watchlist`);
  if (!res.ok) throw new Error('Failed to fetch watchlist');
  return res.json();
}

export async function addWatchlist(typeId: number) {
  const res = await fetch(`${API_BASE}/watchlist/${typeId}`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to add watchlist item');
  return res.json();
}

export async function removeWatchlist(typeId: number) {
  const res = await fetch(`${API_BASE}/watchlist/${typeId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to remove watchlist item');
  return res.json();
}

export interface Snipe {
  type_id: number;
  type_name: string;
  best_bid: number;
  best_ask: number;
  units: number;
  net: number;
  net_pct: number;
  z_score: number;
}

export async function getSnipes(
  limit = 20,
  minNet = 0.02,
  epsilon = 0.003,
  z = 2.5,
): Promise<{ snipes: Snipe[] }> {
  const params = new URLSearchParams({
    limit: String(limit),
    min_net: String(minNet),
    epsilon: String(epsilon),
    z: String(z),
  });
  const res = await fetch(`${API_BASE}/snipes?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch snipes');
  return res.json();
}

export interface AuthStatus {
  has_token: boolean;
  expires_at: number;
}

export async function getAuthStatus(): Promise<AuthStatus> {
  const res = await fetch(`${API_BASE}/auth/status`);
  if (!res.ok) throw new Error('Failed to fetch auth status');
  return res.json();
}

export async function connectAuth() {
  const res = await fetch(`${API_BASE}/auth/connect`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to start auth');
  return res.json();
}
