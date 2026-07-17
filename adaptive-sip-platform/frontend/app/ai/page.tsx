'use client'
import { useState, useEffect, useRef } from 'react'
import { api, ChatMsg } from '@/lib/api'

const SUGGESTIONS = [
  'Nifty 50 mein SIP karna chahiye?',
  'HDFC Top 100 Fund kaisa hai?',
  'Adaptive SIP ka sabse bada faayda kya hai?',
  '₹5000/month 20 saal mein kitna banega?',
  'US stocks mein invest karoon ya Indian?',
  '2020 crash mein Adaptive SIP ne kya kiya?',
]

export default function AIPage() {
  const [aiOn,    setAiOn]    = useState<boolean | null>(null)
  const [history, setHistory] = useState<ChatMsg[]>([])
  const [input,   setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.aiStatus().then(s => setAiOn(s.enabled)).catch(() => setAiOn(false))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, loading])

  async function send(msg: string) {
    if (!msg.trim() || loading) return
    const newHistory: ChatMsg[] = [...history, { role: 'user', content: msg }]
    setHistory(newHistory)
    setInput('')
    setLoading(true)
    try {
      const { reply } = await api.chat(msg, history)
      setHistory([...newHistory, { role: 'assistant', content: reply }])
    } catch (e: unknown) {
      setHistory([...newHistory, { role: 'assistant', content: `❌ Error: ${e instanceof Error ? e.message : String(e)}` }])
    } finally {
      setLoading(false)
    }
  }

  if (aiOn === null) return <div className="text-slate-400 py-20 text-center">Checking AI status...</div>

  if (!aiOn) return (
    <div className="max-w-lg mx-auto py-20 text-center space-y-6">
      <p className="text-5xl">🤖</p>
      <h1 className="text-2xl font-bold text-white">AI Agent OFF Hai</h1>
      <p className="text-slate-400">Admin panel mein API key daalo aur AI enable karo.</p>
      <a href={process.env.NEXT_PUBLIC_ADMIN_URL ?? '#'} target="_blank"
        className="btn-primary inline-block px-8 py-3">
        ⚙️ Admin Panel Kholo →
      </a>
      <p className="text-slate-600 text-sm">Claude (Anthropic) ya Gemini (Google) — dono kaam karte hain</p>
    </div>
  )

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-4">
        <h1 className="section-title">🤖 AI Research Agent</h1>
        <p className="section-sub">Stocks, funds, SIP ke baare mein kuch bhi poocho — real financial knowledge se jawab milega</p>
      </div>

      {/* Suggestions (show only when empty) */}
      {history.length === 0 && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
          {SUGGESTIONS.map(s => (
            <button key={s} onClick={() => send(s)}
              className="card text-left text-sm text-slate-300 hover:border-brand/50 hover:text-white transition p-4">
              💭 {s}
            </button>
          ))}
        </div>
      )}

      {/* Chat history */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-1">
        {history.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-5 py-3 text-sm whitespace-pre-wrap leading-relaxed ${
              msg.role === 'user'
                ? 'bg-brand/20 border border-brand/30 text-white rounded-br-sm'
                : 'bg-slate-800 border border-slate-700 text-slate-200 rounded-bl-sm'
            }`}>
              {msg.role === 'assistant' && <span className="text-brand font-bold mr-2">🤖</span>}
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 border border-slate-700 rounded-2xl rounded-bl-sm px-5 py-3 text-sm text-slate-400">
              🤖 <span className="animate-pulse">Soch raha hai...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-3">
        <input
          className="input flex-1"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send(input)}
          placeholder="Kuch bhi poocho — stocks, funds, SIP, market..."
          disabled={loading}
        />
        <button onClick={() => send(input)} disabled={loading || !input.trim()} className="btn-primary px-6">
          Send
        </button>
        {history.length > 0 && (
          <button onClick={() => setHistory([])} className="btn-ghost px-4 text-slate-500 text-sm">
            Clear
          </button>
        )}
      </div>
      <p className="text-xs text-slate-600 mt-2 text-center">
        Educational tool — SEBI-registered advisor nahi hai. Invest karne se pehle khud research karo.
      </p>
    </div>
  )
}
