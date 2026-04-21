'use client'
import Link from 'next/link'
import { useState, useEffect } from 'react'

const NAV_LINKS = [
  { label: 'Features',  href: '#approach'  },
  { label: 'Analytics', href: '#analytics' },
  { label: 'Install',   href: '#install'   },
  { label: 'Docs',      href: '/docs'      },
]

export function Nav() {
  const [scrolled, setScrolled]     = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-[#090c15]/95 backdrop-blur-xl border-b border-white/[0.06]'
          : 'bg-transparent'
      }`}
    >
      <nav className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">

        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5">
          <svg viewBox="0 0 32 32" fill="none" className="w-7 h-7 flex-shrink-0">
            <path d="M4 4 L16 16 L28 4"  stroke="#22d3ee" strokeWidth="2.5" strokeLinecap="round"/>
            <path d="M4 28 L16 16 L28 28" stroke="#22d3ee" strokeWidth="2.5" strokeLinecap="round"/>
            <circle cx="16" cy="16" r="2.5" fill="#22d3ee"/>
          </svg>
          <span className="font-mono font-bold text-white tracking-wider text-sm">NEXARQ</span>
        </Link>

        {/* Center links */}
        <ul className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(({ label, href }) => (
            <li key={label}>
              <Link
                href={href}
                className="px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/[0.06] transition-all duration-150"
              >
                {label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Right CTAs */}
        <div className="hidden md:flex items-center gap-3">
          <a
            href="https://github.com/nexarq/nexarq"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
            </svg>
            GitHub
          </a>
          <a
            href="#install"
            className="px-4 py-2 bg-cyan-400 text-[#090c15] text-sm font-semibold rounded-lg hover:bg-cyan-300 transition-colors"
          >
            Get Started
          </a>
        </div>

        {/* Mobile toggle */}
        <button
          className="md:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/[0.06] transition-all"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            {mobileOpen
              ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
              : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16"/>}
          </svg>
        </button>
      </nav>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-white/[0.06] bg-[#090c15]/98 backdrop-blur-xl">
          <div className="max-w-6xl mx-auto px-6 py-4 space-y-1">
            {NAV_LINKS.map(({ label, href }) => (
              <Link
                key={label}
                href={href}
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/[0.06] transition-all"
              >
                {label}
              </Link>
            ))}
            <div className="pt-3 mt-2 border-t border-white/[0.06]">
              <a
                href="#install"
                className="block text-center px-4 py-2.5 bg-cyan-400 text-[#090c15] text-sm font-semibold rounded-lg"
              >
                Get Started
              </a>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}
