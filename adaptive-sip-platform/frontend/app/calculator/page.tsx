'use client'
import { useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

function rupee(n: number) { return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` }

export default function CalculatorPage() {
  const [sip,    setSip]    = useState(10000)
  const [rate,   setRate]   = useState(12)
  const [years,  setYears]  = useState(10)
  const [done,   setDone]   = useState(false)

  function calc() {
    const n = years * 12, r = rate / 100 / 12
    return r > 0 ? sip * ((Math.pow(1 + r, n) - 1) / r) * (1 + r) : sip * n
  }

  const corpus   = done ? calc() : 0
  const invested = done ? sip * years * 12 : 0
  const profit   = corpus - invested
  const gain     = invested > 0 ? (profit / invested * 100) : 0

  const pieData = [
    { name: 'Invested', value: Math.round(invested) },
    { name: 'Profit',   value: Math.round(profit)   },
  ]

  // Year-by-year
  const yearRows = Array.from({ length: years }, (_, i) => {
    const n = (i + 1) * 12, r = rate / 100 / 12
    const c = r > 0 ? sip * ((Math.pow(1 + r, n) - 1) / r) * (1 + r) : sip * n
    const inv = sip * n
    return { year: i + 1, invested: inv, corpus: c, profit: c - inv }
  })

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <div>
        <h1 className="section-title">🧮 SIP Calculator</h1>
        <p className="section-sub">Monthly SIP daalo → compound magic dekho</p>
      </div>

      {/* Inputs */}
      <div className="card space-y-6">
        <div>
          <label className="label">Monthly SIP Amount</label>
          <div className="flex items-center gap-4">
            <input type="range" min={500} max={100000} step={500} value={sip}
              onChange={e => setSip(+e.target.value)} className="flex-1 accent-brand" />
            <input type="number" value={sip} onChange={e => setSip(+e.target.value)}
              className="input w-32 text-right" />
          </div>
          <p className="text-brand font-bold text-lg mt-1">{rupee(sip)}/month</p>
        </div>

        <div>
          <label className="label">Expected Annual Return (%)</label>
          <div className="flex items-center gap-4">
            <input type="range" min={4} max={30} step={0.5} value={rate}
              onChange={e => setRate(+e.target.value)} className="flex-1 accent-brand" />
            <input type="number" value={rate} onChange={e => setRate(+e.target.value)}
              className="input w-24 text-right" step={0.5} />
          </div>
          <div className="flex gap-2 mt-2">
            {[8, 10, 12, 15, 18].map(r => (
              <button key={r} onClick={() => setRate(r)}
                className={`text-xs px-3 py-1 rounded-lg border transition ${rate === r ? 'border-brand text-brand bg-brand/10' : 'border-slate-700 text-slate-500 hover:border-slate-500'}`}>
                {r}% {r===12 ? '(Nifty avg)' : r===8 ? '(FD)' : r===15 ? '(small-cap)' : ''}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="label">Investment Period (Years)</label>
          <div className="flex items-center gap-4">
            <input type="range" min={1} max={40} step={1} value={years}
              onChange={e => setYears(+e.target.value)} className="flex-1 accent-brand" />
            <input type="number" value={years} onChange={e => setYears(+e.target.value)}
              className="input w-24 text-right" />
          </div>
          <div className="flex gap-2 mt-2">
            {[5, 10, 15, 20, 30].map(y => (
              <button key={y} onClick={() => setYears(y)}
                className={`text-xs px-3 py-1 rounded-lg border transition ${years === y ? 'border-brand text-brand bg-brand/10' : 'border-slate-700 text-slate-500 hover:border-slate-500'}`}>
                {y}yr
              </button>
            ))}
          </div>
        </div>

        <button onClick={() => setDone(true)} className="btn-primary w-full py-3 text-base">
          🧮 Calculate
        </button>
      </div>

      {/* Results */}
      {done && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="metric-tile">
              <span className="metric-label">Total Invested</span>
              <span className="metric-value text-xl">{rupee(invested)}</span>
            </div>
            <div className="metric-tile border-brand/40">
              <span className="metric-label">Estimated Corpus</span>
              <span className="metric-value text-xl text-brand">{rupee(corpus)}</span>
            </div>
            <div className="metric-tile border-green-700/40">
              <span className="metric-label">Profit Earned</span>
              <span className="metric-value text-xl text-green-400">{rupee(profit)}</span>
              <span className="metric-delta-pos">+{gain.toFixed(1)}% gain</span>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-bold text-white mb-4">Corpus Breakdown</h3>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value">
                    <Cell fill="#667eea" />
                    <Cell fill="#16a34a" />
                  </Pie>
                  <Tooltip formatter={(v: number) => rupee(v)}
                    contentStyle={{ background:'#1e293b', border:'1px solid #334155', borderRadius:8 }} />
                  <Legend wrapperStyle={{ color:'#94a3b8', fontSize:12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="card space-y-2 overflow-y-auto max-h-64">
              <h3 className="font-bold text-white mb-3">Year-by-Year Growth</h3>
              <table className="w-full text-sm">
                <thead><tr className="text-slate-500 text-xs">
                  <th className="text-left pb-2">Year</th>
                  <th className="text-right pb-2">Invested</th>
                  <th className="text-right pb-2">Corpus</th>
                  <th className="text-right pb-2">Profit</th>
                </tr></thead>
                <tbody>
                  {yearRows.map(r => (
                    <tr key={r.year} className="border-t border-slate-800">
                      <td className="py-1.5 text-slate-400">{r.year}</td>
                      <td className="py-1.5 text-right text-slate-400">{rupee(r.invested)}</td>
                      <td className="py-1.5 text-right text-white">{rupee(r.corpus)}</td>
                      <td className="py-1.5 text-right text-green-400">{rupee(r.profit)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card bg-brand/5 border-brand/30 text-sm text-slate-400">
            💡 <strong className="text-white">Tip:</strong> Nifty 50 ka 20-year average return ~12% raha hai.
            Ye sirf estimate hai — actual returns market pe depend karte hain.
          </div>
        </>
      )}
    </div>
  )
}
