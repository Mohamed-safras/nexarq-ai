const AGENTS = [
  { name: 'security',      active: true  },
  { name: 'secrets',       active: true  },
  { name: 'bugs',          active: true  },
  { name: 'performance',   active: true  },
  { name: 'type-safety',   active: true  },
  { name: 'architecture',  active: false },
  { name: 'compliance',    active: true  },
  { name: 'concurrency',   active: false },
  { name: 'deep-analysis', active: true  },
  { name: 'refactor',      active: false },
  { name: 'style',         active: true  },
  { name: 'test-coverage', active: false },
]

export function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden pt-16">

      {/* Background */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-10%,rgba(34,211,238,0.07),transparent)]" />
        <div className="grid-overlay absolute inset-0" />
      </div>

      {/* Scan line */}
      <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-400/20 to-transparent animate-scan pointer-events-none" />

      <div className="relative z-10 w-full max-w-5xl mx-auto px-6 text-center">

        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-8 rounded-full border border-cyan-400/20 bg-cyan-400/[0.06] text-xs font-mono text-cyan-400 uppercase tracking-widest">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          31 Agents · Open Source · Zero Cost
        </div>

        {/* Headline */}
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white mb-6 leading-[1.05]">
          Code review by<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-cyan-400 to-cyan-500">
            31 AI agents
          </span>
          <br />in parallel.
        </h1>

        <p className="text-gray-400 text-lg max-w-xl mx-auto mb-10 leading-relaxed">
          Security flaws, bugs, performance issues, and architecture debt — caught automatically on every commit. Free forever. No credits. No paywalls.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-20">
          <a
            href="#install"
            className="w-full sm:w-auto px-7 py-3 bg-cyan-400 text-[#090c15] font-semibold text-sm rounded-xl hover:bg-cyan-300 transition-colors shadow-[0_0_32px_rgba(34,211,238,0.2)]"
          >
            Get Started Free →
          </a>
          <a
            href="https://github.com/nexarq/nexarq"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full sm:w-auto px-7 py-3 border border-white/[0.1] text-white font-medium text-sm rounded-xl hover:bg-white/[0.05] hover:border-white/20 transition-all"
          >
            View on GitHub
          </a>
        </div>

        {/* Agent nexus panel */}
        <div id="agents" className="relative mx-auto max-w-3xl">
          <div className="border border-white/[0.08] rounded-2xl bg-[#0e1221]/90 backdrop-blur-sm overflow-hidden shadow-[0_32px_64px_rgba(0,0,0,0.4),0_0_40px_rgba(34,211,238,0.05)]">

            {/* Window chrome */}
            <div className="flex items-center gap-2 px-5 py-3.5 border-b border-white/[0.06] bg-black/20">
              <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
              <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
              <div className="w-3 h-3 rounded-full bg-[#27c93f]" />
              <span className="ml-auto font-mono text-xs text-gray-600">nexarq · agent nexus · live</span>
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse ml-2" />
            </div>

            <div className="p-5 space-y-4">
              {/* Agent grid */}
              <div className="grid grid-cols-3 md:grid-cols-4 gap-2">
                {AGENTS.map((agent) => (
                  <div
                    key={agent.name}
                    className={`flex items-center gap-1.5 px-2.5 py-2 rounded-lg border text-xs font-mono transition-colors ${
                      agent.active
                        ? 'border-cyan-400/20 bg-cyan-400/[0.05] text-cyan-300'
                        : 'border-white/[0.04] bg-white/[0.015] text-gray-600'
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${agent.active ? 'bg-cyan-400' : 'bg-gray-700'}`} />
                    <span className="truncate">{agent.name}</span>
                  </div>
                ))}
              </div>

              {/* Terminal output */}
              <div className="rounded-xl bg-black/50 border border-white/[0.05] p-4 font-mono text-xs text-left space-y-1.5">
                <div className="text-gray-600">$ nexarq run --mode=deep</div>
                <div className="text-cyan-400">✓ Extracting diff — 14 files, +847 −203 lines</div>
                <div className="text-gray-300">→ Dispatching 9 agents in parallel...</div>
                <div className="text-yellow-400">⚠ security: SQL injection risk in /api/query <span className="text-yellow-600">(HIGH)</span></div>
                <div className="text-red-400">✗ secrets: hardcoded API key found in config.ts <span className="text-red-600">(CRITICAL)</span></div>
                <div className="text-green-400">✓ performance: no regressions detected</div>
                <div className="flex items-center gap-1 text-gray-500">
                  <span>→ 3 critical · 1 high · 2 medium</span>
                  <span className="animate-blink ml-1">▋</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="absolute bottom-0 inset-x-0 h-40 bg-gradient-to-t from-[#090c15] to-transparent pointer-events-none" />
    </section>
  )
}
