const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function apiFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...opts?.headers },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'API error')
  }
  return res.json()
}

export const api = {
  health: ()                    => apiFetch<{ status: string; version: string }>('/health'),
  tickerUniverses: ()           => apiFetch<Record<string, string[]>>('/api/ticker-universes'),
  search: (ticker: string, start: string, end: string) =>
    apiFetch<SearchResult>(`/api/search?ticker=${encodeURIComponent(ticker)}&start=${start}&end=${end}`),
  backtest: (body: BacktestReq)  => apiFetch<BacktestResult>('/api/backtest', { method:'POST', body: JSON.stringify(body) }),
  batch:    (body: BatchReq)     => apiFetch<BatchResult>('/api/batch',    { method:'POST', body: JSON.stringify(body) }),
  chat:     (message: string, history: ChatMsg[]) =>
    apiFetch<{ reply: string }>('/api/ai/chat', { method:'POST', body: JSON.stringify({ message, history }) }),
  aiStatus: () => apiFetch<{ enabled: boolean; provider: string }>('/api/ai/status'),
}

// ── Types ──────────────────────────────────────────────────────────────────
export interface BacktestReq {
  source: 'synthetic' | 'yahoo'
  ticker?: string
  start: string
  end: string
  use_cache?: boolean
}
export interface BatchReq {
  universe: string
  strategy: 'adaptive' | 'traditional'
  start: string
  end: string
}
export interface PricePoint { Date: string; Price: number }
export interface SearchResult {
  ticker: string; points: number
  start_price: number; end_price: number; total_return_pct: number
  data: PricePoint[]
}
export interface Transaction { Date: string; Price: number; 'Market State': string; 'Current SIP': number; 'Portfolio Value': number; 'Total Investment': number; 'Drawdown %': number }
export interface StrategyResult { strategy_name: string; summary: Record<string, unknown>; transactions: Transaction[] }
export interface BacktestResult { asset_name: string; comparison: unknown; results: Record<string, StrategyResult>; price_data: PricePoint[] }
export interface BatchResult { universe: string; total: number; success: number; errors: number; leaderboard: Record<string, unknown>[]; error_list: unknown[] }
export interface ChatMsg { role: 'user' | 'assistant'; content: string }
