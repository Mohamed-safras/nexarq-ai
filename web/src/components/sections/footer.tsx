const PRODUCT_LINKS  = ['Documentation', 'Changelog', 'Roadmap', 'GitHub Action']
const COMMUNITY_LINKS = ['GitHub', 'Discord', 'Twitter / X', 'Contributing']
const LEGAL_LINKS     = ['Privacy', 'Terms', 'Security']

export function Footer() {
  return (
    <footer className="relative border-t border-white/[0.06] py-16">
      <div className="max-w-6xl mx-auto px-6">

        <div className="grid md:grid-cols-4 gap-10 mb-12">

          {/* Brand */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-2.5 mb-4">
              <svg viewBox="0 0 32 32" fill="none" className="w-7 h-7">
                <path d="M4 4 L16 16 L28 4"  stroke="#22d3ee" strokeWidth="2.5" strokeLinecap="round"/>
                <path d="M4 28 L16 16 L28 28" stroke="#22d3ee" strokeWidth="2.5" strokeLinecap="round"/>
                <circle cx="16" cy="16" r="2.5" fill="#22d3ee"/>
              </svg>
              <span className="font-mono font-bold text-white tracking-wider text-sm">NEXARQ</span>
            </div>
            <p className="text-sm text-gray-500 leading-relaxed max-w-xs">
              Free, open-source AI code review. 31 specialized agents run in parallel on every commit — security, bugs, performance, and more.
            </p>
            <div className="mt-5 flex items-center gap-3">
              <a
                href="https://github.com/nexarq/nexarq"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-3 py-2 border border-white/[0.08] rounded-lg text-xs text-gray-400 hover:text-white hover:border-white/20 transition-all font-mono"
              >
                <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                GitHub
              </a>
            </div>
          </div>

          {/* Product links */}
          <div>
            <p className="text-xs text-gray-600 uppercase tracking-widest font-mono mb-4">Product</p>
            <ul className="space-y-2.5">
              {PRODUCT_LINKS.map((item) => (
                <li key={item}>
                  <a href="#" className="text-sm text-gray-500 hover:text-gray-300 transition-colors">{item}</a>
                </li>
              ))}
            </ul>
          </div>

          {/* Community links */}
          <div>
            <p className="text-xs text-gray-600 uppercase tracking-widest font-mono mb-4">Community</p>
            <ul className="space-y-2.5">
              {COMMUNITY_LINKS.map((item) => (
                <li key={item}>
                  <a href="#" className="text-sm text-gray-500 hover:text-gray-300 transition-colors">{item}</a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-white/[0.05] flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="font-mono text-xs text-gray-600">
            © {new Date().getFullYear()} Nexarq · MIT License · Free forever
          </p>
          <div className="flex items-center gap-6">
            {LEGAL_LINKS.map((item) => (
              <a key={item} href="#" className="font-mono text-xs text-gray-600 hover:text-gray-400 transition-colors">
                {item}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  )
}
