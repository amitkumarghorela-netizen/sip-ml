'use client'
import { useState } from 'react'
import { api, BacktestResult, Transaction } from '@/lib/api'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts'

function StateBadge({ state }: { state: string }) {
  const map: Record<string, string> = {
    BULL: 'badge-bull', BEAR: 'badge-bear', SIDEWAYS: 'badge-side',
    RECOVERY: 'badge-rec', 'NEW HIGH': 'badge-high', FIXED: 'badge-fixed', START: 'badge-fixed',
  }
  return <span className={map[state] ?? 'badge-fixed'}>{state}</span>
}

function MetricCard({ label, value, delta, positive }: { label: string; value: string; delta?: string; positive?: boolean }) {
  return (
    <div className="metric-tile">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {delta && <span className={positive ? 'metric-delta-pos' : 'metric-delta-neg'}>{delta}</span>}
    </div>
  )
}

const POPULAR = ['Synthetic Demo', '^NSEI', 'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'SPY', 'AAPL']

export default function BacktestPage() {
  const [source, setSource]   = useState<'synthetic' | 'yahoo'>('synthetic')
  const [ticker, setTicker]   = useState('^NSEI')
  const [start,  setStart]    = useState('2015-01-01')
  const [end,    setEnd]      = useState('2025-01-01')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const [result,  setResult]  = useState<BacktestResult | null>(null)

  async function run() {
    setLoading(true); setError(''); setResult(null)
    try {
      const res = await api.backtest({ source, ticker: source === 'yahoo' ? ticker : undefined, start, end })
      setResult(res)
    } catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setLoading(false) }
  }

  const keys    = result ? Object.keys(result.results) : []
  const kTrad   = keys.find(k => k.includes('traditional')) ?? keys[0]
  const kAdap   = keys.find(k => k.includes('adaptive'))    ?? keys[1]

  function sf(v: unknown) {
    try { return parseFloat(String(v).replace('%','').replace(',','')) } catch { return 0 }
  }

  // Build chart data aligned by date
  function buildChartData() {
    if (!result || !kTrad || !kAdap) return []
    const tradTxns: Transaction[] = result.results[kTrad]?.transactions ?? []
    const adapTxns: Transaction[] = result.results[kAdap]?.transactions ?? []
    return tradTxns.map((t, i) => ({
      date:      t.Date?.slice(0,7),
      tradValue: t['Portfolio Value'] ?? 0,
      adapValue: adapTxns[i]?.['Portfolio Value'] ?? 0,
      invested:  t['Total Investment'] ?? 0,
      tradSIP:   t['Current SIP'] ?? 0,
      adapSIP:   adapTxns[i]?.['Current SIP'] ?? 0,
      drawdown:  adapTxns[i]?.['Drawdown %'] ?? 0,
    }))
  }
  const chartData = buildChartData()

  const tradSum = result?.results[kTrad]?.summary ?? {}
  const adapSum = result?.results[kAdap]?.summary ?? {}
  const adapWins = [
    { k: 'XIRR %', low: false }, { k: 'CAGR %', low: false },
    { k: 'Sharpe Ratio', low: false }, { k: 'Max Drawdown %', low: true },
    { k: 'Total Return %', low: false },
  ].filter(({ k, low }) => {
    const tv = sf(tradSum[k]); const av = sf(adapSum[k])
    return low ? av < tv : av > tv
  }).length

  return (
    <div className="space-y-8">
      <div>
        <h1 className="section-title">⚡ Run Backtest</h1>
        <p className="section-sub">Adaptive SIP vs Traditional SIP — kaun jita? 🟢 better, 🔴 worse dikhega</p>
      </div>

      {/* Form */}
      <div className="card space-y-4">
        <div className="flex gap-4 flex-wrap">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="radio" checked={source==='synthetic'} onChange={()=>setSource('synthetic')} className="accent-brand" />
            <span className="text-sm text-slate-300">🎲 Synthetic Demo (no internet)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="radio" checked={source==='yahoo'} onChange={()=>setSource('yahoo')} className="accent-brand" />
            <span className="text-sm text-slate-300">🌐 Yahoo Finance (real data)</span>
          </label>
        </div>

        {source === 'yahoo' && (
          <div>
            <label className="label">Ticker</label>
            <div className="flex gap-2 flex-wrap">
              {POPULAR.slice(1).map(t => (
                <button key={t} onClick={()=>setTicker(t)}
                  className={`text-xs px-3 py-1 rounded-lg border transition ${ticker===t ? 'border-brand text-brand bg-brand/10' : 'border-slate-700 text-slate-400 hover:border-slate-500'}`}>
                  {t}
                </button>
              ))}
            </div>
            <input className="input mt-2" value={ticker} onChange={e=>setTicker(e.target.value)} placeholder="e.g. RELIANCE.NS" />
          </div>
        )}

        <div className="grid sm:grid-cols-2 gap-4">
          <div><label className="label">Start Date</label><input type="date" className="input" value={start} onChange={e=>setStart(e.target.value)} /></div>
          <div><label className="label">End Date</label>  <input type="date" className="input" value={end}   onChange={e=>setEnd(e.target.value)}   /></div>
        </div>

        <button onClick={run} disabled={loading} className="btn-primary w-full py-3 text-base">
          {loading ? '⏳ Running backtest...' : '🚀 Run Backtest'}
        </button>
        {error && <p className="text-red-400 text-sm bg-red-950/50 border border-red-800 rounded-lg p-3">{error}</p>}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-8">
          {/* Winner banner */}
          {adapWins >= 3
            ? <div className="card bg-green-950/50 border-green-700 text-center space-y-1">
                <p className="text-2xl">🏆</p>
                <p className="text-green-400 font-bold text-lg">Adaptive SIP NE JEETA! ({adapWins}/5 metrics)</p>
                <p className="text-slate-400 text-sm">Smart investing pays off 💪</p>
              </div>
            : <div className="card bg-blue-950/50 border-blue-700 text-center space-y-1">
                <p className="text-2xl">ℹ️</p>
                <p className="text-blue-400 font-bold text-lg">Mixed result is dataset pe</p>
                <p className="text-slate-400 text-sm">Adaptive SIP volatile/bear markets mein shines karta hai</p>
              </div>
          }

          {/* Metrics side by side */}
          <div className="grid md:grid-cols-2 gap-6">
            <div className="card space-y-4">
              <h2 className="font-bold text-white">📌 Traditional SIP</h2>
              <div className="grid grid-cols-2 gap-3">
                {['XIRR %','CAGR %','Sharpe Ratio','Max Drawdown %','Total Return %'].map(k => (
                  <MetricCard key={k} label={k} value={`${sf(tradSum[k]).toFixed(2)}${k.includes('%') ? '%' : ''}`} />
                ))}
              </div>
            </div>
            <div className="card space-y-4">
              <h2 className="font-bold text-white">🚀 Adaptive SIP v1.1</h2>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { k: 'XIRR %', low: false }, { k: 'CAGR %', low: false },
                  { k: 'Sharpe Ratio', low: false }, { k: 'Max Drawdown %', low: true },
                  { k: 'Total Return %', low: false },
                ].map(({ k, low }) => {
                  const tv = sf(tradSum[k]); const av = sf(adapSum[k])
                  const better = low ? av < tv : av > tv
                  const diff = av - tv
                  return (
                    <MetricCard key={k} label={k}
                      value={`${av.toFixed(2)}${k.includes('%') ? '%' : ''}`}
                      delta={`${diff >= 0 ? '+' : ''}${diff.toFixed(2)}${k.includes('%') ? '%' : ''}`}
                      positive={better} />
                  )
                })}
              </div>
            </div>
          </div>

          {/* Portfolio Growth Chart */}
          <div className="card space-y-4">
            <h2 className="font-bold text-white">📈 Portfolio Growth</h2>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData}>
                <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} interval={11} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} axisLine={false}
                  tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                <Tooltip contentStyle={{ background:'#1e293b', border:'1px solid #334155', borderRadius:8 }}
                  formatter={(v: number, n: string) => [`₹${v.toLocaleString()}`, n]} labelStyle={{ color:'#94a3b8' }} />
                <Legend wrapperStyle={{ color:'#94a3b8', fontSize:12 }} />
                <Line type="monotone" dataKey="tradValue" stroke="#6b7280" name="Traditional" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="adapValue" stroke="#667eea" name="Adaptive" dot={false} strokeWidth={2.5} />
                <Line type="monotone" dataKey="invested"  stroke="#374151" name="Invested"  dot={false} strokeWidth={1} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* SIP Amount Chart */}
          <div className="card space-y-4">
            <h2 className="font-bold text-white">💰 Monthly SIP Amount</h2>
            <p className="text-slate-500 text-xs">🔴 Peak = bear market mein zyada invest (SALE!) · 🔵 Low = bull market (mehnga)</p>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData}>
                <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} interval={11} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} axisLine={false}
                  tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                <Tooltip contentStyle={{ background:'#1e293b', border:'1px solid #334155', borderRadius:8 }}
                  formatter={(v: number) => [`₹${v.toLocaleString()}`]} />
                <Area type="monotone" dataKey="adapSIP" stroke="#667eea" fill="#667eea22" name="Adaptive SIP" strokeWidth={2} />
                <Area type="monotone" dataKey="tradSIP" stroke="#6b7280" fill="#6b728022" name="Traditional SIP" strokeWidth={1} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Transaction table — Adaptive */}
          {kAdap && (
            <div className="card space-y-4">
              <h2 className="font-bold text-white">📅 Adaptive SIP — Monthly Log</h2>
              <div className="overflow-x-auto max-h-80 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-slate-900">
                    <tr className="text-slate-500 text-xs uppercase">
                      {['Date','Price','Market State','SIP','Portfolio Value','Drawdown %'].map(h => (
                        <th key={h} className="text-left py-2 px-3 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.results[kAdap].transactions.map((t, i) => (
                      <tr key={i} className="border-t border-slate-800 hover:bg-slate-800/50">
                        <td className="py-2 px-3 text-slate-400">{t.Date?.slice(0,7)}</td>
                        <td className="py-2 px-3">₹{Number(t.Price).toLocaleString()}</td>
                        <td className="py-2 px-3"><StateBadge state={t['Market State']} /></td>
                        <td className="py-2 px-3 font-medium">₹{Number(t['Current SIP']).toLocaleString()}</td>
                        <td className="py-2 px-3">₹{Number(t['Portfolio Value']).toLocaleString()}</td>
                        <td className={`py-2 px-3 ${Number(t['Drawdown %']) > 10 ? 'text-red-400' : 'text-slate-400'}`}>
                          {Number(t['Drawdown %']).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
