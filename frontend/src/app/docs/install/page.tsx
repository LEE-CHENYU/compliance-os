"use client";

import { useState } from "react";

type AppId = "claude-code" | "claude-desktop" | "codex";

const APPS: { id: AppId; label: string; sub: string; configPath: string; language: "json" | "toml" }[] = [
  { id: "claude-code",    label: "Claude Code",    sub: "Anthropic CLI",         configPath: "~/.claude/settings.json", language: "json" },
  { id: "claude-desktop", label: "Claude Desktop", sub: "macOS / Windows / Linux app", configPath: "~/Library/Application Support/Claude/claude_desktop_config.json", language: "json" },
  { id: "codex",          label: "Codex CLI",      sub: "OpenAI CLI",            configPath: "~/.codex/config.toml",    language: "toml" },
];

const STDIO_JSON = `{
  "mcpServers": {
    "guardian": {
      "command": "/ABSOLUTE/PATH/TO/PYTHON",
      "args": ["-m", "compliance_os.mcp_server"],
      "env": {
        "GUARDIAN_API_URL": "https://guardiancompliance.app",
        "GUARDIAN_TOKEN": "gdn_oc_YOUR_TOKEN"
      }
    }
  }
}`;

const STDIO_TOML = `[mcp_servers.guardian]
type = "stdio"
command = "/ABSOLUTE/PATH/TO/PYTHON"
args = ["-m", "compliance_os.mcp_server"]

[mcp_servers.guardian.env]
GUARDIAN_API_URL = "https://guardiancompliance.app"
GUARDIAN_TOKEN = "gdn_oc_YOUR_TOKEN"`;

const SSE_JSON = `{
  "mcpServers": {
    "guardian": {
      "url": "https://guardiancompliance.app/mcp/sse",
      "headers": { "Authorization": "Bearer gdn_oc_YOUR_TOKEN" }
    }
  }
}`;

const SSE_TOML = `[mcp_servers.guardian]
type = "http"
url = "https://guardiancompliance.app/mcp/sse"

[mcp_servers.guardian.http_headers]
Authorization = "Bearer gdn_oc_YOUR_TOKEN"`;

function CodeBlock({ code, lang }: { code: string; lang?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative group">
      <button
        onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
        className="absolute top-2 right-2 px-2 py-1 rounded-md text-[10px] font-semibold bg-white/10 text-[#b3c4dd] hover:bg-white/20 transition-colors opacity-0 group-hover:opacity-100"
      >
        {copied ? "copied" : "copy"}
      </button>
      <pre className="bg-[#0d1424] text-[#c7d4e8] rounded-xl p-4 text-[11px] leading-relaxed overflow-auto font-mono whitespace-pre">
        {lang && <div className="text-[9px] uppercase tracking-[0.16em] text-[#556a8c] mb-2">{lang}</div>}
        {code}
      </pre>
    </div>
  );
}

export default function InstallDocsPage() {
  const [app, setApp] = useState<AppId>("claude-code");
  const [mode, setMode] = useState<"stdio" | "sse">("stdio");
  const selected = APPS.find((a) => a.id === app)!;
  const snippet = mode === "stdio"
    ? (selected.language === "json" ? STDIO_JSON : STDIO_TOML)
    : (selected.language === "json" ? SSE_JSON : SSE_TOML);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4fa] via-white to-[#e8edf5]">
      {/* Header */}
      <header className="border-b border-blue-100/30 bg-white/80 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2.5 group" aria-label="Guardian home">
            <div style={{width:22, height:22, display:'flex', flexDirection:'column', gap:2.5, transform:'perspective(200px) rotateX(-8deg) rotateY(12deg)'}} className="group-hover:opacity-90 transition-opacity">
              <div style={{height:4.5, background:'linear-gradient(135deg, #5b8dee, #4a74d4)', borderRadius:1, width:22, transform:'translateX(2px)'}} />
              <div style={{height:4.5, background:'linear-gradient(135deg, #5b8dee, #4a74d4)', borderRadius:1, width:22, transform:'translateX(-1px)'}} />
              <div style={{height:4.5, background:'linear-gradient(135deg, #5b8dee, #4a74d4)', borderRadius:1, width:22, transform:'translateX(3px)'}} />
            </div>
            <span className="text-sm font-bold tracking-tight text-[#0d1424]">Guardian</span>
            <span className="text-sm text-[#8b97ad] font-normal hidden sm:inline">· Docs</span>
          </a>
          <a href="/connect" className="text-xs font-semibold text-[#3a5a8c] hover:text-[#1a2036]">Get token →</a>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12 space-y-10">
        {/* Hero */}
        <section>
          <div className="text-[10px] uppercase tracking-[0.18em] text-[#8b97ad] mb-2">Install Guardian MCP</div>
          <h1 className="text-3xl font-bold text-[#0d1424] mb-3">Connect Guardian to your AI tools</h1>
          <p className="text-sm text-[#556480] max-w-2xl leading-relaxed">
            Guardian runs as an MCP server. Once connected, Claude Code, Claude Desktop, or Codex can check your compliance status, scan folders against case templates, fill forms, and search Gmail — all from the chat prompt.
          </p>
        </section>

        {/* Fastest path: the agent does it */}
        <section className="rounded-2xl bg-[#0d1424] text-white p-8 shadow-sm">
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="flex-1 min-w-[260px]">
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#7ba6ff] mb-2">Fastest path · 60 seconds</div>
              <h2 className="text-xl font-semibold mb-3">Let your agent install it</h2>
              <p className="text-sm text-[#b3c4dd] leading-relaxed mb-4">
                Paste this one line to your Claude Code or Codex session. The agent will fetch the install instructions, configure your client, and verify the connection — no menu clicks.
              </p>
              <CodeBlock code="Install Guardian MCP by following https://guardiancompliance.app/AGENTS.md" />
            </div>
            <div className="flex flex-col gap-2 text-xs text-[#7ba6ff] pt-7">
              <a href="/AGENTS.md" className="underline underline-offset-4 decoration-[#7ba6ff]/40 hover:decoration-[#7ba6ff]">Read AGENTS.md →</a>
            </div>
          </div>
        </section>

        {/* Manual path */}
        <section>
          <div className="text-[10px] uppercase tracking-[0.18em] text-[#8b97ad] mb-2">Manual path</div>
          <h2 className="text-xl font-semibold text-[#0d1424] mb-6">Three steps, by hand</h2>

          {/* Step 1: install */}
          <div className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6 mb-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-xs font-bold flex items-center justify-center">1</div>
              <h3 className="text-sm font-semibold text-[#0d1424]">Install the Python package</h3>
            </div>
            <p className="text-xs text-[#556480] mb-3">Requires Python 3.11+. Use whichever env manager you already have.</p>
            <CodeBlock code={`pip install "compliance-os[agent]"`} lang="bash" />
          </div>

          {/* Step 2: token */}
          <div className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6 mb-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-xs font-bold flex items-center justify-center">2</div>
              <h3 className="text-sm font-semibold text-[#0d1424]">Get your auth token</h3>
            </div>
            <p className="text-xs text-[#556480] mb-3">
              Open <a href="/connect" className="text-[#3a5a8c] underline underline-offset-2 font-medium">guardiancompliance.app/connect</a>, sign in, click <strong>Generate token</strong>. The token starts with <code className="bg-blue-50 text-[#3a5a8c] px-1 rounded text-[11px]">gdn_oc_</code>.
            </p>
            <p className="text-xs text-[#8b97ad]">
              Skip this step if you&apos;re running Guardian locally on <code className="bg-blue-50 text-[#3a5a8c] px-1 rounded text-[11px]">localhost:8000</code> — an empty token auto-auths via the dev JWT flow.
            </p>
          </div>

          {/* Step 3: config */}
          <div className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-xs font-bold flex items-center justify-center">3</div>
              <h3 className="text-sm font-semibold text-[#0d1424]">Write the config</h3>
            </div>

            <p className="text-xs text-[#556480] mb-4">Easiest — use the installer:</p>
            <div className="mb-6">
              <CodeBlock
                code={`GUARDIAN_TOKEN="gdn_oc_YOUR_TOKEN" \\
guardian-mcp install --auto`}
                lang="bash"
              />
            </div>

            <div className="border-t border-blue-100/40 pt-6">
              <p className="text-xs text-[#556480] mb-4">…or edit the config file yourself. Pick your host:</p>

              <div className="flex gap-2 mb-4 flex-wrap">
                {APPS.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => setApp(a.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      app === a.id
                        ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-sm"
                        : "bg-white border border-blue-100/50 text-[#556480] hover:border-blue-200"
                    }`}
                  >
                    {a.label}
                  </button>
                ))}
              </div>

              <div className="mb-3 text-[11px] text-[#8b97ad]">
                {selected.sub} — edit <code className="bg-blue-50 text-[#3a5a8c] px-1 py-0.5 rounded font-mono">{selected.configPath}</code>
              </div>

              <div className="flex gap-2 mb-3 text-[11px]">
                <button
                  onClick={() => setMode("stdio")}
                  className={`px-2.5 py-1 rounded-md transition-colors ${mode === "stdio" ? "bg-blue-100 text-[#3a5a8c] font-semibold" : "text-[#8b97ad] hover:text-[#556480]"}`}
                >
                  stdio (Python install)
                </button>
                <button
                  onClick={() => setMode("sse")}
                  className={`px-2.5 py-1 rounded-md transition-colors ${mode === "sse" ? "bg-blue-100 text-[#3a5a8c] font-semibold" : "text-[#8b97ad] hover:text-[#556480]"}`}
                >
                  hosted SSE (no install)
                </button>
              </div>

              <CodeBlock code={snippet} lang={selected.language} />

              <p className="text-[11px] text-[#8b97ad] mt-3">
                {mode === "stdio" ? (
                  <>Replace <code className="bg-blue-50 text-[#3a5a8c] px-1 rounded font-mono">/ABSOLUTE/PATH/TO/PYTHON</code> with the path from <code className="bg-blue-50 text-[#3a5a8c] px-1 rounded font-mono">python -c &quot;import sys; print(sys.executable)&quot;</code>.</>
                ) : (
                  <>Hosted SSE runs on our servers — no Python install needed. Lighter setup, slightly higher latency.</>
                )}
              </p>
            </div>
          </div>
        </section>

        {/* Verify */}
        <section className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6">
          <h2 className="text-sm font-semibold text-[#0d1424] mb-3">4. Verify</h2>
          <p className="text-xs text-[#556480] mb-3">Restart your app (fully quit Claude Desktop; re-run the CLI). Then ask:</p>
          <div className="bg-blue-50/50 rounded-lg p-4 text-sm text-[#3a5a8c] font-medium">
            &quot;What&apos;s my Guardian compliance status?&quot;
          </div>
          <p className="text-[11px] text-[#8b97ad] mt-3">
            If you see a formatted summary — you&apos;re done. If the tool isn&apos;t listed, your config didn&apos;t load. If it errors &quot;Cannot reach Guardian API&quot;, re-check the token and URL.
          </p>
        </section>

        {/* Tool catalog */}
        <section className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6">
          <h2 className="text-sm font-semibold text-[#0d1424] mb-4">What you get · 23 tools</h2>
          <div className="grid sm:grid-cols-2 gap-4 text-xs text-[#556480]">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[#8b97ad] font-semibold mb-1.5">Compliance context</div>
              <div className="space-y-0.5 font-mono text-[11px] text-[#3a5a8c]">
                <div>guardian_status</div>
                <div>guardian_deadlines</div>
                <div>guardian_risks</div>
                <div>guardian_documents</div>
                <div>guardian_ask</div>
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[#8b97ad] font-semibold mb-1.5">Case templates</div>
              <div className="space-y-0.5 font-mono text-[11px] text-[#3a5a8c]">
                <div>case_active_search</div>
                <div>h1b_active_search</div>
                <div>cpa_active_search</div>
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[#8b97ad] font-semibold mb-1.5">Documents</div>
              <div className="space-y-0.5 font-mono text-[11px] text-[#3a5a8c]">
                <div>parse_document</div>
                <div>classify_document</div>
                <div>upload_document</div>
                <div>batch_upload</div>
                <div>query_documents</div>
                <div>index_documents</div>
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[#8b97ad] font-semibold mb-1.5">Forms &amp; Gmail</div>
              <div className="space-y-0.5 font-mono text-[11px] text-[#3a5a8c]">
                <div>generate_form_8843</div>
                <div>run_compliance_check</div>
                <div>get_filing_guidance</div>
                <div>gmail_search / read / draft</div>
                <div>gmail_send / reply / download_attachment</div>
              </div>
            </div>
          </div>
        </section>

        <footer className="text-center text-[11px] text-[#a6b0c5] py-6">
          Questions? <a href="mailto:fretin13@gmail.com" className="underline underline-offset-2">fretin13@gmail.com</a>
        </footer>
      </main>
    </div>
  );
}
