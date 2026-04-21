const FEATURES = [
  {
    tag: 'Zero friction',
    headline: 'Drop it in. It works.',
    body: 'One command installs Nexarq globally. Git hooks self-register. No config files, no dashboards, no accounts. Every commit is reviewed automatically from the first run.',
    stat: '< 60s',
    statLabel: 'to first review',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    tag: 'Non-blocking',
    headline: 'Never slows your flow.',
    body: 'Agents run asynchronously — your git push completes instantly. Tier-1 agents cover critical issues pre-push. Scheduled deep reviews run all 31 agents without any friction.',
    stat: '31',
    statLabel: 'specialized agents',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
      </svg>
    ),
  },
  {
    tag: 'Full coverage',
    headline: 'OWASP. CVEs. Architecture.',
    body: 'Tier-1 covers the full OWASP Top 10, secrets detection, and critical bugs. Tier-2 expands to performance, concurrency, type-safety, and architectural drift — all in one pass.',
    stat: '100%',
    statLabel: 'OWASP Top 10',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75l2.25 2.25L15 9.75m-3 10.5a9 9 0 110-18 9 9 0 010 18z" />
      </svg>
    ),
  },
]

export function Approach() {
  return (
    <section id="approach" className="relative py-32 overflow-hidden">
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />

      <div className="max-w-5xl mx-auto px-6">

        {/* Section header */}
        <div className="mb-16">
          <p className="font-mono text-xs text-cyan-400 uppercase tracking-widest mb-4">How it works</p>
          <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight leading-[1.1]">
            Built for developers<br />
            <span className="text-gray-500">who ship fast.</span>
          </h2>
        </div>

        {/* Feature cards */}
        <div className="grid md:grid-cols-3 gap-5">
          {FEATURES.map((f) => (
            <div
              key={f.tag}
              className="group relative flex flex-col border border-white/[0.06] rounded-2xl bg-[#0e1221] p-6 hover:border-cyan-400/20 hover:bg-[#101525] transition-all duration-300 overflow-hidden"
            >
              {/* Top accent */}
              <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

              {/* Icon */}
              <div className="w-10 h-10 rounded-xl border border-white/[0.08] bg-white/[0.04] flex items-center justify-center text-cyan-400 mb-5">
                {f.icon}
              </div>

              {/* Tag */}
              <p className="font-mono text-xs text-cyan-400/60 uppercase tracking-widest mb-2">{f.tag}</p>

              {/* Headline */}
              <h3 className="text-lg font-semibold text-white mb-3 leading-snug">{f.headline}</h3>

              {/* Body */}
              <p className="text-sm text-gray-500 leading-relaxed flex-1">{f.body}</p>

              {/* Stat */}
              <div className="mt-6 pt-5 border-t border-white/[0.06]">
                <div className="text-2xl font-bold font-mono text-cyan-400">{f.stat}</div>
                <div className="text-xs font-mono text-gray-600 mt-0.5">{f.statLabel}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Tier comparison */}
        <div className="mt-8 border border-white/[0.06] rounded-2xl bg-[#0e1221] p-6 md:p-8">
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                <p className="font-mono text-xs text-cyan-400 uppercase tracking-widest">Tier 1 — Pre-push</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {['security', 'secrets', 'bugs', 'deep-analysis'].map((a) => (
                  <span key={a} className="px-2.5 py-1 rounded-lg border border-cyan-400/15 bg-cyan-400/[0.05] font-mono text-xs text-cyan-300">
                    {a}
                  </span>
                ))}
              </div>
              <p className="text-xs text-gray-600 mt-3">Runs on every push. Critical-only. Never blocks.</p>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="w-2 h-2 rounded-full bg-gray-500" />
                <p className="font-mono text-xs text-gray-500 uppercase tracking-widest">Tier 2 — Scheduled</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {['performance', 'type-safety', 'architecture', 'compliance', 'concurrency', 'refactor', 'style', 'test-coverage'].map((a) => (
                  <span key={a} className="px-2.5 py-1 rounded-lg border border-white/[0.06] bg-white/[0.02] font-mono text-xs text-gray-500">
                    {a}
                  </span>
                ))}
              </div>
              <p className="text-xs text-gray-600 mt-3">Runs on schedule or `nexarq run --deep`. Full coverage.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="absolute bottom-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
    </section>
  )
}
