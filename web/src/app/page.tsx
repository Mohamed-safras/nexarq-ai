import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6">
      {/* Ad slot — top of page */}
      <div id="nexarq-ad-top" className="w-full max-w-2xl mb-8 text-center">
        {/* Carbon Ads / EthicalAds renders here via script in layout */}
      </div>

      <div className="max-w-2xl w-full space-y-10">
        {/* Hero */}
        <div className="space-y-4">
          <h1 className="text-4xl font-bold tracking-tight text-zinc-100">
            nexarq
          </h1>
          <p className="text-zinc-400 text-lg leading-relaxed">
            Security-first, multi-agent code review on every git commit.
            <br />
            <span className="text-cyan-400">
              Free. Open-source. No paywalls.
            </span>
          </p>
        </div>

        {/* Install options */}
        <div className="space-y-3">
          <p className="text-zinc-500 text-sm uppercase tracking-widest">
            Install
          </p>

          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-2 font-mono text-sm">
            <div>
              <span className="text-zinc-500"># npm (recommended)</span>
              <pre className="text-cyan-300 mt-1">npm install -g nexarq</pre>
            </div>
            <div className="border-t border-zinc-800 pt-2">
              <span className="text-zinc-500"># macOS / Linux</span>
              <pre className="text-cyan-300 mt-1">
                {"curl -fsSL https://nexarq.dev/install.sh | bash"}
              </pre>
            </div>
            <div className="border-t border-zinc-800 pt-2">
              <span className="text-zinc-500"># Windows (PowerShell)</span>
              <pre className="text-cyan-300 mt-1">
                {"irm https://nexarq.dev/install.ps1 | iex"}
              </pre>
            </div>
          </div>
        </div>

        {/* Quick start */}
        <div className="space-y-3">
          <p className="text-zinc-500 text-sm uppercase tracking-widest">
            Quick Start
          </p>
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 font-mono text-sm space-y-1">
            <pre className="text-zinc-300">
              nexarq init <span className="text-zinc-600"># setup wizard</span>
            </pre>
            <pre className="text-zinc-300">
              nexarq run{" "}
              <span className="text-zinc-600"># review last commit</span>
            </pre>
            <pre className="text-zinc-300">
              nexarq code{" "}
              <span className="text-cyan-300">"fix the auth bug"</span>
            </pre>
          </div>
        </div>

        {/* Agent count */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          {[
            {
              label: "31 agents",
              desc: "security, bugs, performance, and more",
            },
            { label: "4 providers", desc: "Ollama, OpenAI, Anthropic, Google" },
            {
              label: "Free forever",
              desc: "no credits, no limits, no paywalls",
            },
            { label: "Open source", desc: "MIT license, self-hostable" },
          ].map(({ label, desc }) => (
            <div
              key={label}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-4"
            >
              <p className="text-cyan-400 font-semibold">{label}</p>
              <p className="text-zinc-500 text-xs mt-1">{desc}</p>
            </div>
          ))}
        </div>

        {/* Links */}
        <nav className="flex gap-6 text-sm text-zinc-500">
          <Link href="/docs" className="hover:text-zinc-200 transition-colors">
            Docs
          </Link>
          <Link
            href="/dashboard"
            className="hover:text-zinc-200 transition-colors"
          >
            Dashboard
          </Link>
          <a
            href="https://github.com/nexarq/nexarq"
            className="hover:text-zinc-200 transition-colors"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
        </nav>
      </div>

      {/* Ad slot — bottom of page */}
      <div
        id="nexarq-ad-bottom"
        className="w-full max-w-2xl mt-16 text-center text-xs text-zinc-700"
      >
        Nexarq is free — supported by unobtrusive ads.{" "}
        <Link href="/ads" className="underline hover:text-zinc-500">
          Learn more
        </Link>
      </div>
    </main>
  );
}
