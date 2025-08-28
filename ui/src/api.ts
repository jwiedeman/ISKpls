export const API_BASE = 'http://localhost:8000';

export interface StatusLog {
  type: string;
  runId?: string;
  level?: string;
  message?: string;
}

export interface StatusSnapshot {
  inflight?: unknown[];
  last_runs?: { job: string; ok: boolean; ts?: string; ms?: number }[];
  counts?: Record<string, number>;
  esi?: { remain?: number; reset?: number };
  queue?: Record<string, number>;
  logs?: StatusLog[];
}

export async function getStatus(): Promise<StatusSnapshot> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error('Failed to fetch status');
  return res.json();
}

export interface Coverage {
  types_indexed: number;
  books_10m: number;
  median_age_s: number;
  distinct_types_24h: number;
}

export async function getCoverage(): Promise<Coverage> {
  const res = await fetch(`${API_BASE}/coverage`);
  if (!res.ok) throw new Error('Failed to fetch coverage');
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

export async function runJob(name: string, verbose = false) {
  const url = new URL(`${API_BASE}/jobs/${name}/run`);
  if (verbose) url.searchParams.set('verbose', 'true');
  const res = await fetch(url.toString(), { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run job');
  return res.json();
}

export async function buildRecommendations(
  dryRun = false,
  verbose = false,
) {
  const url = new URL(`${API_BASE}/recommendations/build`);
  if (dryRun) url.searchParams.set('dry_run', 'true');
  if (verbose) url.searchParams.set('verbose', 'true');
  const res = await fetch(url.toString(), { method: 'POST' });
  if (!res.ok) throw new Error('Failed to build recommendations');
  return res.json();
}

export interface RecParams {
  limit?: number;
  offset?: number;
  sort?: string;
  dir?: string;
  search?: string;
  min_profit_pct?: number;
  min_mom?: number;
  min_vol?: number;
  show_all?: boolean;
}

export async function getRecommendations(params: RecParams = {}) {
  const qs = new URLSearchParams();
  if (params.limit !== undefined) qs.set('limit', String(params.limit));
  if (params.offset !== undefined) qs.set('offset', String(params.offset));
  if (params.sort) qs.set('sort', params.sort);
  if (params.dir) qs.set('dir', params.dir);
  if (params.search) qs.set('search', params.search);
  if (params.min_profit_pct !== undefined)
    qs.set('min_profit_pct', String(params.min_profit_pct));
  if (params.min_mom !== undefined) qs.set('min_mom', String(params.min_mom));
  if (params.min_vol !== undefined) qs.set('min_vol', String(params.min_vol));
  if (params.show_all) qs.set('show_all', 'true');
  qs.set('mode', 'profit_only');
  const res = await fetch(`${API_BASE}/recommendations?${qs.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch recommendations');
  return res.json();
}

export interface DbParams {
  limit?: number;
  offset?: number;
  sort?: string;
  dir?: string;
  search?: string;
  deal?: string[];
  min_profit_pct?: number;
}

export async function getDbItems(params: DbParams = {}) {
  const qs = new URLSearchParams();
  if (params.limit !== undefined) qs.set('limit', String(params.limit));
  if (params.offset !== undefined) qs.set('offset', String(params.offset));
  if (params.sort) qs.set('sort', params.sort);
  if (params.dir) qs.set('dir', params.dir);
  if (params.search) qs.set('search', params.search);
  if (params.min_profit_pct !== undefined)
    qs.set('min_profit_pct', String(params.min_profit_pct));
  if (params.deal)
    for (const d of params.deal) qs.append('deal', d);
  const res = await fetch(`${API_BASE}/db/items?${qs.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch db items');
  return res.json();
}

export interface DbItem {
  type_id: number;
  type_name: string;
  best_bid: number | null;
  best_ask: number | null;
  last_updated: string;
  fresh_ms: number;
  profit_pct: number;
  profit_isk: number;
  deal: string;
  mom?: number | null;
  est_daily_vol?: number | null;
  has_both_sides: boolean;
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

export interface RepriceGuidance {
  type_id: number;
  type_name: string;
  best_bid: number;
  best_ask: number;
  buy_price: number;
  sell_price: number;
  buy_net_pct: number;
  sell_net_pct: number;
}

export async function getRepriceGuidance(typeId: number): Promise<RepriceGuidance> {
  const res = await fetch(`${API_BASE}/orders/reprice?type_id=${typeId}`);
  if (!res.ok) throw new Error('Failed to fetch reprice guidance');
  return res.json();
}

export async function getPortfolioNav() {
  const res = await fetch(`${API_BASE}/portfolio/nav`);
  if (!res.ok) throw new Error('Failed to fetch portfolio NAV');
  return res.json();
}

export async function getPortfolioSummary(basis: 'mark' | 'quicksell' = 'mark') {
  const res = await fetch(`${API_BASE}/portfolio/summary?basis=${basis}`);
  if (!res.ok) throw new Error('Failed to fetch portfolio summary');
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
