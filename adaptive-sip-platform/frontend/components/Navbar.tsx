'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const nav = [
  { href: '/',           label: '🏠 Home'       },
  { href: '/backtest',   label: '⚡ Backtest'   },
  { href: '/calculator', label: '🧮 Calculator' },
  { href: '/ai',         label: '🤖 AI Agent'   },
]

export default function Navbar() {
  const path = usePathname()
  const adminUrl = process.env.NEXT_PUBLIC_ADMIN_URL || '#'

  return (
    <nav className="fixed top-0 inset-x-0 z-50 bg-slate-950/80 backdrop-blur border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 font-bold text-white text-lg">
          <span className="text-2xl">📈</span>
          <span>ASRP</span>
          <span className="text-xs text-slate-500 font-normal hidden sm:block">Adaptive SIP Platform</span>
        </Link>

        {/* Links */}
        <div className="flex items-center gap-1">
          {nav.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`px-3 py-1.5 rounded-lg text-sm transition ${
                path === href
                  ? 'bg-brand/20 text-brand font-semibold'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {label}
            </Link>
          ))}
          <a
            href={adminUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-3 px-3 py-1.5 rounded-lg text-xs text-slate-500 border border-slate-700 hover:border-slate-500 hover:text-slate-300 transition"
          >
            ⚙️ Admin
          </a>
        </div>
      </div>
    </nav>
  )
}
