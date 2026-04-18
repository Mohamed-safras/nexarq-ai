export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-[#1a1b26] text-[#c0caf5] font-mono p-8">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[#7dcfff]">NEXARQ</h1>
        <p className="text-[#565f89] text-sm">Security dashboard</p>
      </div>

      {/* Security posture score + severity counts */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <div className="col-span-2 md:col-span-1 bg-[#16161e] border border-[#565f89] rounded p-4">
          <div className="text-[#565f89] text-xs mb-1">POSTURE SCORE</div>
          <div className="text-4xl font-bold text-[#9ece6a]">—</div>
          <div className="text-[#565f89] text-xs mt-1">connect a repo</div>
        </div>
        {[
          { label: 'CRITICAL', color: 'text-[#f7768e]' },
          { label: 'HIGH',     color: 'text-[#ff9e64]' },
          { label: 'MEDIUM',   color: 'text-[#e0af68]' },
          { label: 'LOW',      color: 'text-[#7dcfff]' },
        ].map((item) => (
          <div key={item.label} className="bg-[#16161e] border border-[#565f89] rounded p-4">
            <div className={`${item.color} text-xs mb-1`}>{item.label}</div>
            <div className="text-2xl font-bold">—</div>
          </div>
        ))}
      </div>

      {/* 30-day trend chart */}
      <div className="bg-[#16161e] border border-[#565f89] rounded p-4 mb-8">
        <div className="text-[#565f89] text-xs mb-3">
          30-DAY TREND ·{' '}
          <span className="text-[#7dcfff]">GET /api/v1/trends?repo=owner/repo</span>
        </div>
        <div className="flex items-end gap-0.75 h-28 border-b border-[#565f89]">
          {Array.from({ length: 30 }, (_, i) => (
            <div
              key={i}
              className="flex-1 bg-[#565f89] opacity-30 rounded-t"
              style={{ height: `${20 + Math.random() * 80}%` }}
            />
          ))}
        </div>
        <div className="text-[#565f89] text-xs mt-2">
          Populate via GitHub webhook or{' '}
          <span className="text-[#7dcfff]">nexarq-action</span>
        </div>
      </div>

      {/* Setup guide */}
      <div className="bg-[#16161e] border border-[#565f89] rounded p-4 mb-8">
        <div className="text-[#565f89] text-xs mb-3">QUICK SETUP</div>
        <div className="space-y-3">
          {[
            { step: '1', cmd: 'npm install -g nexarq',  note: 'Install CLI' },
            { step: '2', cmd: 'nexarq init',             note: 'Choose provider' },
            { step: '3', cmd: 'nexarq run',              note: 'First review' },
          ].map((item) => (
            <div key={item.step} className="flex items-center gap-3">
              <div className="w-6 h-6 rounded-full bg-[#7dcfff] text-[#1a1b26] text-xs font-bold flex items-center justify-center shrink-0">
                {item.step}
              </div>
              <code className="text-[#7dcfff] text-sm">{item.cmd}</code>
              <span className="text-[#565f89] text-sm">{item.note}</span>
            </div>
          ))}
        </div>
      </div>

      {/* New features highlight */}
      <div className="grid md:grid-cols-2 gap-4 mb-8">
        {[
          { title: 'nexarq watch',   desc: 'Live review as you save — findings before commit' },
          { title: 'nexarq commit',  desc: 'AI-generated commit messages from your diff' },
          { title: 'nexarq explain', desc: 'Plain-English explanation of any file or line range' },
          { title: 'nexarq chat',    desc: 'Persistent conversation about your codebase' },
        ].map((feature) => (
          <div key={feature.title} className="bg-[#16161e] border border-[#565f89] rounded p-4">
            <code className="text-[#7dcfff] text-sm font-bold">{feature.title}</code>
            <p className="text-[#565f89] text-xs mt-1">{feature.desc}</p>
          </div>
        ))}
      </div>

      {/* Carbon Ads slot */}
      <div className="bg-[#16161e] border border-dashed border-[#565f89] rounded p-4 text-center text-[#565f89] text-xs">
        <div id="carbonads" />
        <div>Sponsored — keeps Nexarq free for everyone</div>
      </div>

    </main>
  )
}
