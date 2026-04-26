const STEPS = [
  {
    step: '01',
    title: 'Install globally',
    code: 'npm install -g nexarq',
    comment: '# or: bun add -g nexarq',
  },
  {
    step: '02',
    title: 'Run setup wizard',
    code: 'nexarq init',
    comment: '# picks provider, installs git hook',
  },
  {
    step: '03',
    title: 'Review any diff',
    code: 'nexarq run',
    comment: '# 31 agents · parallel · instant',
  },
]

const PROVIDERS = [
  { name: 'Anthropic', dot: 'bg-orange-400' },
  { name: 'OpenAI',    dot: 'bg-green-400'  },
  { name: 'Google',    dot: 'bg-blue-400'   },
  { name: 'Ollama',    dot: 'bg-purple-400' },
]

export function Install() {
  return (
    <section id="install" className="relative py-32 overflow-hidden">
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-400/15 to-transparent" />

      <div className="max-w-5xl mx-auto px-6">

        {/* Section header */}
        <div className="text-center mb-16">
          <p className="font-mono text-xs text-cyan-400 uppercase tracking-widest mb-4">Install</p>
          <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight leading-[1.1]">
            Up and reviewing<br />
            <span className="text-gray-500">in under a minute.</span>
          </h2>
        </div>

        {/* Steps */}
        <div className="grid md:grid-cols-3 gap-5 mb-8">
          {STEPS.map((s, i) => (
            <div key={s.step} className="relative border border-white/[0.06] rounded-2xl bg-[#0e1221] p-6 group hover:border-cyan-400/20 transition-colors overflow-hidden">
              {/* Connector line (desktop) */}
              {i < STEPS.length - 1 && (
                <div className="hidden md:block absolute top-[2.75rem] right-0 w-5 h-px bg-white/[0.08] translate-x-full z-10" />
              )}
              <div className="font-mono text-xs text-cyan-400/40 mb-4 uppercase tracking-widest">Step {s.step}</div>
              <div className="font-semibold text-white mb-4 leading-snug">{s.title}</div>
              <div className="rounded-xl bg-black/50 border border-white/[0.05] p-3.5 font-mono">
                <div className="text-cyan-300 text-sm">{s.code}</div>
                <div className="text-gray-600 text-xs mt-1">{s.comment}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Providers row */}
        <div className="border border-white/[0.06] rounded-2xl bg-[#0e1221] p-6 flex flex-col md:flex-row items-center justify-between gap-6 mb-12">
          <div>
            <p className="font-mono text-xs text-gray-500 uppercase tracking-widest mb-1.5">Supported Providers</p>
            <p className="text-sm text-gray-400">Bring your own API key — or use Ollama for fully local, private reviews.</p>
          </div>
          <div className="flex items-center gap-2.5 flex-wrap justify-center">
            {PROVIDERS.map((p) => (
              <div key={p.name} className="flex items-center gap-2 px-3 py-2 border border-white/[0.07] rounded-xl bg-white/[0.02] font-mono text-xs text-gray-300">
                <span className={`w-1.5 h-1.5 rounded-full ${p.dot}`} />
                {p.name}
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center">
          <a
            href="https://github.com/nexarq/nexarq"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-3 px-8 py-4 bg-cyan-400 text-[#090c15] font-semibold text-sm rounded-xl hover:bg-cyan-300 transition-colors shadow-[0_0_40px_rgba(34,211,238,0.2)]"
          >
            <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
            </svg>
            Star on GitHub — Free Forever
          </a>
          <p className="text-xs text-gray-600 font-mono mt-4">MIT License · No account required · Works offline with Ollama</p>
        </div>
      </div>
    </section>
  )
}
