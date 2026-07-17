import Link from 'next/link'

const features = [
  { icon: '⚡', title: 'Run Backtest', desc: 'Compare Adaptive vs Traditional SIP on any stock. Green = better.', href: '/backtest' },
  { icon: '🧮', title: 'SIP Calculator', desc: 'See how much your monthly SIP grows over years with compound interest.', href: '/calculator' },
  { icon: '🤖', title: 'AI Research Agent', desc: 'Ask anything — Reliance acchi hai? Nifty mein SIP karoon? AI batayega.', href: '/ai' },
]

const states = [
  { cls: 'badge-bear',  label: 'BEAR 🔴',     desc: 'Market gira → zyada invest karo (SALE!)' },
  { cls: 'badge-bull',  label: 'BULL 🟢',     desc: 'Market upar → kam invest karo (mehnga)' },
  { cls: 'badge-side',  label: 'SIDEWAYS 🟡', desc: 'Market flat → same rakho' },
  { cls: 'badge-rec',   label: 'RECOVERY 🔵', desc: 'Sudhar ho raha → high SIP rakho' },
  { cls: 'badge-high',  label: 'NEW HIGH 💚', desc: 'All-time high → SIP aur kam karo' },
]

export default function HomePage() {
  return (
    <div className="space-y-16">

      {/* Hero */}
      <section className="text-center py-16 space-y-6">
        <div className="inline-flex items-center gap-2 bg-brand/10 border border-brand/30 text-brand px-4 py-1.5 rounded-full text-sm font-medium">
          📈 Logic Freeze v1.1 · Strategy Engine Active
        </div>
        <h1 className="text-5xl font-bold text-white leading-tight">
          Adaptive SIP<br />
          <span className="bg-gradient-to-r from-brand to-brand-dark bg-clip-text text-transparent">
            Research Platform
          </span>
        </h1>
        <p className="text-slate-400 text-xl max-w-2xl mx-auto">
          Market gire to <strong className="text-red-400">zyada invest karo</strong> (SALE hai!).
          Market uche to <strong className="text-green-400">kam invest karo</strong> (mehnga hai!).
          Smart SIP = better returns.
        </p>
        <div className="flex justify-center gap-4 flex-wrap">
          <Link href="/backtest" className="btn-primary text-base px-8 py-3">
            ⚡ Run Backtest →
          </Link>
          <Link href="/calculator" className="btn-ghost text-base px-6 py-3">
            🧮 SIP Calculator
          </Link>
        </div>
      </section>

      {/* Simple Explanation */}
      <section className="grid md:grid-cols-3 gap-6">
        <div className="card border-l-4 border-l-red-600 space-y-3">
          <p className="text-3xl">📉</p>
          <h3 className="font-bold text-white text-lg">Market Gira (BEAR)</h3>
          <p className="text-slate-400 text-sm">Normal aadmi: ₹10,000 daalta rehta hai</p>
          <p className="text-white text-sm"><strong>Adaptive SIP:</strong> ₹20,000–₹50,000 daalta hai</p>
          <p className="text-red-400 text-xs">👉 SALE chal rahi hai! Sasta milega!</p>
        </div>
        <div className="card border-l-4 border-l-green-600 space-y-3">
          <p className="text-3xl">📈</p>
          <h3 className="font-bold text-white text-lg">Market Ucha (BULL)</h3>
          <p className="text-slate-400 text-sm">Normal aadmi: ₹10,000 daalta rehta hai</p>
          <p className="text-white text-sm"><strong>Adaptive SIP:</strong> ₹5,000 daalta hai</p>
          <p className="text-green-400 text-xs">👉 Sab mehnga — zyada khareedna waste!</p>
        </div>
        <div className="card border-l-4 border-l-amber-500 space-y-3">
          <p className="text-3xl">➡️</p>
          <h3 className="font-bold text-white text-lg">Market Flat (SIDEWAYS)</h3>
          <p className="text-slate-400 text-sm">Normal aadmi: ₹10,000</p>
          <p className="text-white text-sm"><strong>Adaptive SIP:</strong> ₹10,000</p>
          <p className="text-amber-400 text-xs">👉 Koi change nahi, wait karo</p>
        </div>
      </section>

      {/* Features */}
      <section className="space-y-4">
        <h2 className="text-2xl font-bold text-white text-center">🚀 Kya-Kya Kar Sakte Ho</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((f) => (
            <Link key={f.href} href={f.href}
              className="card hover:border-brand/50 hover:bg-slate-800/50 transition group space-y-3">
              <span className="text-4xl">{f.icon}</span>
              <h3 className="font-bold text-white group-hover:text-brand transition">{f.title}</h3>
              <p className="text-slate-400 text-sm">{f.desc}</p>
              <span className="text-brand text-sm font-medium">Open →</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Color guide */}
      <section className="card space-y-4">
        <h2 className="text-xl font-bold text-white">🎨 Color Code Guide — Ek Nazar Mein Samjho</h2>
        <div className="flex flex-wrap gap-4">
          {states.map((s) => (
            <div key={s.label} className="flex-1 min-w-40 space-y-2">
              <span className={s.cls}>{s.label}</span>
              <p className="text-slate-400 text-xs">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Quick start */}
      <section className="card bg-gradient-to-br from-brand/10 to-brand-dark/10 border-brand/30 text-center space-y-4">
        <h2 className="text-xl font-bold text-white">⚡ 3 Steps Mein Shuru Karo</h2>
        <div className="flex justify-center gap-8 flex-wrap text-sm text-slate-300">
          <div><span className="text-brand font-bold">1.</span> Backtest page pe jao</div>
          <div><span className="text-brand font-bold">2.</span> "Synthetic Demo" select karo</div>
          <div><span className="text-brand font-bold">3.</span> Run Backtest dabao — result dekho!</div>
        </div>
        <Link href="/backtest" className="btn-primary inline-block">⚡ Start Backtest →</Link>
      </section>

    </div>
  )
}
