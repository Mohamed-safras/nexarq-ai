const SEVERITY_DATA = [
  { label: 'Critical', count: 3,  pct: 30,  color: 'bg-red-500'    },
  { label: 'High',     count: 7,  pct: 70,  color: 'bg-orange-400' },
  { label: 'Medium',   count: 12, pct: 100, color: 'bg-yellow-400' },
  { label: 'Low',      count: 5,  pct: 50,  color: 'bg-blue-400'   },
  { label: 'Info',     count: 9,  pct: 80,  color: 'bg-gray-500'   },
]

const AGENT_PERF = [
  { name: 'security',    ms: 1240, findings: 4 },
  { name: 'secrets',     ms: 890,  findings: 1 },
  { name: 'bugs',        ms: 1560, findings: 6 },
  { name: 'performance', ms: 1100, findings: 3 },
  { name: 'type-safety', ms: 970,  findings: 2 },
]

const STATS = [
  { metric: '4.2s',  label: 'avg review time' },
  { metric: '99.3%', label: 'uptime'          },
  { metric: '31',    label: 'parallel agents' },
  { metric: '4',     label: 'LLM providers'   },
]

const GRAPH_NODES = [
  { x: 50, y: 12, r: 14, label: 'ORCHESTRATOR', primary: true },
  { x: 18, y: 42, r: 9,  label: 'SEC',  primary: false },
  { x: 36, y: 46, r: 9,  label: 'BUG',  primary: false },
  { x: 54, y: 44, r: 9,  label: 'PERF', primary: false },
  { x: 72, y: 42, r: 9,  label: 'ARCH', primary: false },
  { x: 18, y: 70, r: 7,  label: 'CVE',  primary: false },
  { x: 36, y: 73, r: 7,  label: 'MEM',  primary: false },
  { x: 54, y: 72, r: 7,  label: 'TYPE', primary: false },
  { x: 72, y: 70, r: 7,  label: 'DOCS', primary: false },
  { x: 50, y: 92, r: 10, label: 'SUMMARY', primary: false },
]

const EDGES: [number, number][] = [
  [0,1],[0,2],[0,3],[0,4],
  [1,5],[2,6],[3,7],[4,8],
  [5,9],[6,9],[7,9],[8,9],
]

export function Analytics() {
  return (
    <section id="analytics" className="relative py-32 grid-dense overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-[#090c15] via-transparent to-[#090c15] pointer-events-none" />

      <div className="relative z-10 max-w-6xl mx-auto px-6">

        {/* Section header */}
        <div className="text-center mb-16">
          <p className="font-mono text-xs text-cyan-400 uppercase tracking-widest mb-4">Analytics</p>
          <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight leading-[1.1]">
            Full visibility into<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-cyan-500">every review run.</span>
          </h2>
        </div>

        {/* Stat row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {STATS.map((s) => (
            <div key={s.label} className="border border-white/[0.06] rounded-2xl bg-[#0e1221]/80 p-5 text-center">
              <div className="text-3xl font-bold font-mono text-cyan-400">{s.metric}</div>
              <div className="text-xs font-mono text-gray-600 mt-1 uppercase tracking-widest">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Three data panels */}
        <div className="grid md:grid-cols-3 gap-5">

          {/* Severity breakdown */}
          <div className="border border-white/[0.06] rounded-2xl bg-[#0e1221]/80 backdrop-blur p-6">
            <p className="font-mono text-xs text-gray-500 uppercase tracking-widest mb-5">Severity Breakdown</p>
            <div className="space-y-4">
              {SEVERITY_DATA.map((row) => (
                <div key={row.label}>
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-sm text-gray-400">{row.label}</span>
                    <span className="font-mono text-xs text-white font-semibold">{row.count}</span>
                  </div>
                  <div className="h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                    <div
                      className={`h-full ${row.color} rounded-full opacity-75 transition-all`}
                      style={{ width: `${row.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 pt-4 border-t border-white/[0.05] flex justify-between">
              <span className="text-xs text-gray-600">Total findings</span>
              <span className="font-mono text-sm font-semibold text-white">36</span>
            </div>
          </div>

          {/* Agent performance */}
          <div className="border border-white/[0.06] rounded-2xl bg-[#0e1221]/80 backdrop-blur p-6">
            <p className="font-mono text-xs text-gray-500 uppercase tracking-widest mb-5">Agent Performance</p>
            <div className="space-y-1">
              {AGENT_PERF.map((agent) => (
                <div key={agent.name} className="flex items-center justify-between py-2.5 border-b border-white/[0.04] last:border-0">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 flex-shrink-0" />
                    <span className="text-sm text-gray-300 font-mono">{agent.name}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-xs text-gray-600">{agent.ms}ms</span>
                    <span className="font-mono text-xs text-cyan-400 font-semibold w-14 text-right">{agent.findings} found</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Agent graph */}
          <div className="border border-white/[0.06] rounded-2xl bg-[#0e1221]/80 backdrop-blur p-6">
            <p className="font-mono text-xs text-gray-500 uppercase tracking-widest mb-5">Agent Graph</p>
            <svg viewBox="0 0 100 105" className="w-full h-52" fill="none">
              {EDGES.map(([from, to], i) => {
                const a = GRAPH_NODES[from]!
                const b = GRAPH_NODES[to]!
                return (
                  <line
                    key={i}
                    x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                    stroke="#22d3ee" strokeWidth="0.4" strokeOpacity="0.2"
                    strokeDasharray="2 2"
                  />
                )
              })}
              {GRAPH_NODES.map((node, i) => (
                <g key={i}>
                  <circle
                    cx={node.x} cy={node.y} r={node.r}
                    stroke="#22d3ee"
                    strokeWidth={node.primary ? 0.8 : 0.5}
                    strokeOpacity={node.primary ? 0.8 : 0.3}
                    fill="#0e1221"
                  />
                  <text
                    x={node.x} y={node.y}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={node.primary ? '3.2' : '2.6'}
                    fill="#22d3ee"
                    fillOpacity={node.primary ? 0.9 : 0.5}
                    fontFamily="monospace"
                  >
                    {node.label}
                  </text>
                </g>
              ))}
            </svg>
            <div className="flex justify-between text-xs font-mono text-gray-600">
              <span>Fan-out · parallel</span>
              <span>↓ aggregation</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
