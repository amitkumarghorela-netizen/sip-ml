import type { Metadata } from 'next'
import './globals.css'
import Navbar from '@/components/Navbar'

export const metadata: Metadata = {
  title: 'ASRP — Adaptive SIP Research Platform',
  description: 'Smart SIP investing — buy more when market falls, less when it rises',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950">
        <Navbar />
        <main className="pt-14 max-w-7xl mx-auto px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  )
}
