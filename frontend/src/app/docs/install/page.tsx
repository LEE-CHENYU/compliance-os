"use client";

import { useState } from "react";
import { Logo } from "@/components/Logo";

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
          <Logo subtitle="Docs" />
          <a href="/connect" className="text-xs font-semibold text-[#3a5a8c] hover:text-[#1a2036]">Get token →</a>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12 space-y-10">
        {/* Hero */}
        <section>
          <div className="text-[10px] uppercase tracking-[0.18em] text-[#8b97ad] mb-2">Install Guardian</div>
          <h1 className="text-3xl font-bold text-[#0d1424] mb-3">Connect Guardian to your AI tools</h1>
          <p className="text-sm text-[#556480] max-w-2xl leading-relaxed mb-5">
            Guardian runs in two places — in your <strong>coding agent</strong> (Claude Code, Claude Desktop, Codex) as 23 MCP tools, and in your <strong>chat apps</strong> (WhatsApp, Telegram, Discord, Slack) via OpenClaw. Same data room, same compliance intelligence.
          </p>
          <div className="flex gap-2 flex-wrap">
            <a href="#mcp" className="text-xs px-3 py-1.5 rounded-lg bg-blue-50 text-[#3a5a8c] font-semibold hover:bg-blue-100 transition-colors">Code · MCP (Claude / Codex)</a>
            <a href="#chat" className="text-xs px-3 py-1.5 rounded-lg bg-blue-50 text-[#3a5a8c] font-semibold hover:bg-blue-100 transition-colors">Chat · OpenClaw (WhatsApp / Telegram / ...)</a>
          </div>
        </section>

        {/* MCP anchor */}
        <div id="mcp" className="-mt-4" />

        {/* One-click desktop extension */}
        <section className="rounded-2xl bg-gradient-to-br from-[#f4e7dd] to-[#faf4ee] border border-[#D97757]/20 p-8 shadow-sm">
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="flex-1 min-w-[260px]">
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#b35d3f] mb-2">One click · Claude Desktop</div>
              <h2 className="text-xl font-semibold mb-3 text-[#0d1424]">Download the desktop extension</h2>
              <p className="text-sm text-[#556480] leading-relaxed mb-4">
                Download the <code className="bg-white/70 px-1.5 py-0.5 rounded text-[#b35d3f] font-mono">guardian.dxt</code> file and double-click it. Claude Desktop handles the pip install, prompts you for your token, and wires up the MCP server. No terminal.
              </p>
              <a
                href="/guardian.dxt"
                download="guardian.dxt"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#D97757] text-white font-semibold text-sm shadow-sm hover:shadow-md transition-shadow"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Download guardian.dxt
              </a>
            </div>
            <div className="text-[11px] text-[#8b97ad] pt-7 max-w-[200px]">
              Requires Claude Desktop 0.9+ with Extensions enabled (Settings → Extensions → Developer mode).
            </div>
          </div>
        </section>

        {/* Fastest path: the agent does it */}
        <section className="rounded-2xl bg-[#0d1424] text-white p-8 shadow-sm">
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="flex-1 min-w-[260px]">
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#7ba6ff] mb-2">CLI path · 60 seconds</div>
              <h2 className="text-xl font-semibold mb-3">Let your agent install it</h2>
              <p className="text-sm text-[#b3c4dd] leading-relaxed mb-4">
                Paste this one line to your Claude Code or Codex session. The agent fetches the install instructions, configures your client, and verifies the connection.
              </p>
              <CodeBlock code="Install Guardian MCP by following https://guardiancompliance.app/AGENTS.md" />
              <details className="mt-5 text-sm">
                <summary className="cursor-pointer text-[#7ba6ff] hover:text-white transition-colors">
                  Agent&apos;s workspace blocks URL fetch?
                </summary>
                <div className="mt-3 pl-4 border-l-2 border-[#7ba6ff]/30 space-y-3">
                  <p className="text-[13px] text-[#b3c4dd] leading-relaxed">
                    Enterprise workspaces often have a domain allowlist. Paste this zero-fetch command instead — replace the token with one from <a href="/connect" className="underline underline-offset-2">/connect</a>.
                  </p>
                  <CodeBlock
                    code={`pip install "compliance-os[agent]" && \\
GUARDIAN_TOKEN="gdn_oc_YOUR_TOKEN" \\
GUARDIAN_API_URL="https://guardiancompliance.app" \\
guardian-mcp install --auto`}
                    lang="bash"
                  />
                  <p className="text-[11px] text-[#7ba6ff]/70">
                    Or paste the full <a href="/AGENTS.md" className="underline underline-offset-2">AGENTS.md</a> content into your chat so the agent can follow it without fetching.
                  </p>
                </div>
              </details>
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

        {/* ──────────────────────────────────────────────────── */}
        {/* OpenClaw (chat) */}
        {/* ──────────────────────────────────────────────────── */}
        <div id="chat" className="pt-6 border-t border-blue-100/40">
          <div className="text-[10px] uppercase tracking-[0.18em] text-[#8b97ad] mb-2">Chat · OpenClaw</div>
          <h2 className="text-2xl font-bold text-[#0d1424] mb-3">Guardian in WhatsApp, Telegram, Discord, Slack</h2>
          <p className="text-sm text-[#556480] leading-relaxed max-w-2xl">
            OpenClaw is a router that exposes Guardian as a chat skill, so your clients can message in plain language from any platform they already use. Best for status checks, deadline reminders, and quick questions — no app install.
          </p>
        </div>

        {/* Example queries */}
        <section className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6">
          <h3 className="text-sm font-semibold text-[#0d1424] mb-3">Ask naturally</h3>
          <div className="grid sm:grid-cols-2 gap-2">
            {[
              "Check my compliance status",
              "When are my deadlines?",
              "Do I need to file FBAR?",
              "What documents have I uploaded?",
              "When is my I-20 expiring?",
              "Show me my active findings",
            ].map((q) => (
              <div key={q} className="text-xs text-[#3a5a8c] font-medium bg-blue-50/50 px-3 py-2 rounded-lg">&quot;{q}&quot;</div>
            ))}
          </div>
        </section>

        {/* Install OpenClaw */}
        <section className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6">
          <h3 className="text-sm font-semibold text-[#0d1424] mb-4">Set up in 30 seconds</h3>

          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-xs font-bold flex items-center justify-center shrink-0">1</div>
              <div className="flex-1">
                <div className="text-sm font-semibold text-[#0d1424] mb-1">Install OpenClaw</div>
                <p className="text-xs text-[#556480] mb-2">If you don&apos;t have OpenClaw yet, install from <a href="https://openclaw.io" target="_blank" rel="noopener" className="text-[#3a5a8c] underline underline-offset-2 font-medium">openclaw.io</a> and link it to the chat app(s) you already use.</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-xs font-bold flex items-center justify-center shrink-0">2</div>
              <div className="flex-1">
                <div className="text-sm font-semibold text-[#0d1424] mb-1">Install the Guardian skill</div>
                <CodeBlock code="openclaw skills install guardian-compliance" lang="bash" />
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-xs font-bold flex items-center justify-center shrink-0">3</div>
              <div className="flex-1">
                <div className="text-sm font-semibold text-[#0d1424] mb-1">Paste your token</div>
                <p className="text-xs text-[#556480]">
                  Get a token from <a href="/connect" className="text-[#3a5a8c] underline underline-offset-2 font-medium">guardiancompliance.app/connect</a> (same one you&apos;d use for MCP — they&apos;re scoped identically), then paste it when OpenClaw prompts, or set it in your skill settings as <code className="bg-blue-50 text-[#3a5a8c] px-1 rounded font-mono">GUARDIAN_TOKEN</code>.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-xs font-bold flex items-center justify-center shrink-0">4</div>
              <div className="flex-1">
                <div className="text-sm font-semibold text-[#0d1424] mb-1">Say hi</div>
                <p className="text-xs text-[#556480]">Message <strong>&quot;guardian status&quot;</strong> in any chat where you&apos;ve linked OpenClaw — you should see a compliance summary within a few seconds.</p>
              </div>
            </div>
          </div>

          <div className="mt-5 pt-4 border-t border-blue-100/40 text-[11px] text-[#8b97ad]">
            Tokens are scoped read+write on your data room. Revoke anytime at <a href="/connect" className="text-[#3a5a8c] underline underline-offset-2">/connect</a> (hit <em>Rotate token</em>).
          </div>
        </section>

        <footer className="text-center text-[11px] text-[#a6b0c5] py-6">
          Questions? <a href="mailto:fretin13@gmail.com" className="underline underline-offset-2">fretin13@gmail.com</a>
        </footer>
      </main>
    </div>
  );
}
