"use client";

import { useState, useEffect } from "react";
import { authHeaders, getToken } from "@/lib/auth";

const AUTH_API =
  typeof window !== "undefined" && window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000/api/auth"
    : "/api/auth";

const API_HOST =
  typeof window !== "undefined" && window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : "https://guardiancompliance.app";

type AppId = "claude-desktop" | "claude-code" | "codex";

interface TokenInfo {
  label: string;
  token_prefix: string;
  created_at: string;
}

interface ConnectionStatus {
  api_url: string;
  active_token: TokenInfo | null;
}

function configSnippet(app: AppId, token: string): string {
  const url = `${API_HOST}/mcp`;
  if (app === "codex") {
    return `[mcp_servers.guardian]
type = "http"
url = "${url}/sse"

[mcp_servers.guardian.http_headers]
Authorization = "Bearer ${token || "YOUR_TOKEN"}"`;
  }
  const obj = {
    mcpServers: {
      guardian: {
        url: `${url}/sse`,
        headers: {
          Authorization: `Bearer ${token || "YOUR_TOKEN"}`,
        },
      },
    },
  };
  return JSON.stringify(obj, null, 2);
}

function configPath(app: AppId): string {
  switch (app) {
    case "claude-desktop":
      return "~/Library/Application Support/Claude/claude_desktop_config.json";
    case "claude-code":
      return "~/.claude/settings.json";
    case "codex":
      return "~/.codex/config.toml";
  }
}

const APPS: { id: AppId; label: string; icon: string }[] = [
  { id: "claude-desktop", label: "Claude Desktop", icon: "C" },
  { id: "claude-code", label: "Claude Code", icon: ">" },
  { id: "codex", label: "Codex", icon: "X" },
];

const TOOLS = [
  { name: "Compliance Context", items: ["guardian_status", "guardian_deadlines", "guardian_risks", "guardian_documents", "guardian_ask"], color: "bg-blue-100 text-blue-700" },
  { name: "Form Filing", items: ["generate_form_8843", "run_compliance_check", "get_filing_guidance"], color: "bg-emerald-100 text-emerald-700" },
  { name: "Documents", items: ["upload_document", "batch_upload", "parse_document", "classify_document"], color: "bg-amber-100 text-amber-700" },
  { name: "Gmail", items: ["gmail_search", "gmail_read", "gmail_draft", "gmail_send", "gmail_reply"], color: "bg-purple-100 text-purple-700" },
];

export default function ConnectPage() {
  const [selectedApp, setSelectedApp] = useState<AppId>("claude-desktop");
  const [connection, setConnection] = useState<ConnectionStatus | null>(null);
  const [token, setToken] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<"config" | "token" | null>(null);
  const [step, setStep] = useState(1);
  const isLoggedIn = !!getToken();

  useEffect(() => {
    if (!isLoggedIn) return;
    fetch(`${AUTH_API}/openclaw/connection`, { headers: authHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => data && setConnection(data))
      .catch(() => {});
  }, [isLoggedIn]);

  async function generateToken() {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${AUTH_API}/openclaw/token`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!resp.ok) throw new Error("Failed to generate token");
      const data = await resp.json();
      setToken(data.token);
      setConnection(data);
      setStep(3);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  function copyToClipboard(text: string, type: "config" | "token") {
    navigator.clipboard.writeText(text);
    setCopied(type);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4fa] via-white to-[#e8edf5]">
      {/* Header */}
      <header className="border-b border-blue-100/30 bg-white/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] flex items-center justify-center text-white text-xs font-bold">G</div>
            <span className="text-sm font-semibold text-[#0d1424]">Guardian</span>
          </a>
          <a href="/dashboard" className="text-xs text-[#556480] hover:text-[#3a5a8c] transition-colors">
            Dashboard
          </a>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <h1 className="text-2xl md:text-3xl font-bold text-[#0d1424] mb-3">
            Connect Guardian to your AI tools
          </h1>
          <p className="text-sm md:text-base text-[#556480] max-w-xl mx-auto">
            Access your compliance status, generate forms, and manage documents — directly from Claude Desktop, Claude Code, or Codex. No install required.
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-8">

          {/* Step 1: Choose your app */}
          <section className="bg-white/90 backdrop-blur-xl rounded-2xl border border-blue-100/30 shadow-sm p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${step >= 1 ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white" : "bg-gray-100 text-gray-400"}`}>1</div>
              <h2 className="text-sm font-semibold text-[#0d1424]">Choose your app</h2>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {APPS.map((app) => (
                <button
                  key={app.id}
                  onClick={() => { setSelectedApp(app.id); setStep(Math.max(step, 2)); }}
                  className={`rounded-xl border p-4 text-center transition-all ${
                    selectedApp === app.id
                      ? "border-[#5b8dee] bg-blue-50/50 shadow-sm"
                      : "border-blue-100/30 bg-white hover:border-blue-200/50"
                  }`}
                >
                  <div className={`w-10 h-10 mx-auto mb-2 rounded-xl flex items-center justify-center text-lg font-bold ${
                    selectedApp === app.id ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white" : "bg-gray-100 text-gray-500"
                  }`}>{app.icon}</div>
                  <div className="text-xs font-medium text-[#0d1424]">{app.label}</div>
                </button>
              ))}
            </div>
          </section>

          {/* Step 2: Generate token */}
          <section className={`bg-white/90 backdrop-blur-xl rounded-2xl border border-blue-100/30 shadow-sm p-6 transition-opacity ${step >= 2 ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${step >= 2 ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white" : "bg-gray-100 text-gray-400"}`}>2</div>
              <h2 className="text-sm font-semibold text-[#0d1424]">Get your token</h2>
            </div>

            {!isLoggedIn ? (
              <div className="rounded-xl border border-amber-200/50 bg-amber-50/50 p-4">
                <p className="text-xs text-amber-800 mb-2">Sign in to generate a token.</p>
                <a href="/login" className="inline-block px-4 py-2 rounded-lg text-xs font-semibold bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white">
                  Sign in
                </a>
              </div>
            ) : (
              <div className="space-y-3">
                {connection?.active_token && !token && (
                  <div className="rounded-lg border border-blue-100/40 bg-[#f7f9fd] px-3 py-2">
                    <div className="text-[10px] uppercase tracking-[0.14em] text-[#8b97ad] mb-1">Active token</div>
                    <div className="text-[11px] text-[#556480]">
                      Prefix: <code className="bg-white/80 px-1 rounded text-[#3a5a8c]">{connection.active_token.token_prefix}</code>
                      <span className="mx-2 text-[#ccc]">|</span>
                      Created: {new Date(connection.active_token.created_at).toLocaleDateString()}
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <button
                    onClick={generateToken}
                    disabled={loading}
                    className="px-4 py-2 rounded-lg text-xs font-semibold bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white disabled:opacity-50"
                  >
                    {loading ? "Generating..." : connection?.active_token ? "Rotate token" : "Generate token"}
                  </button>
                  {token && (
                    <button
                      onClick={() => copyToClipboard(token, "token")}
                      className="px-3 py-2 rounded-lg text-xs font-semibold border border-blue-100/50 text-[#3a5a8c] bg-white/70"
                    >
                      {copied === "token" ? "Copied" : "Copy token"}
                    </button>
                  )}
                </div>
                {token && (
                  <code className="block text-[10px] bg-[#f0f3f8] rounded-lg p-3 text-[#3a5a8c] break-all max-h-20 overflow-auto font-mono">
                    {token}
                  </code>
                )}
                {error && <div className="text-[11px] text-red-500">{error}</div>}
              </div>
            )}
          </section>

          {/* Step 3: Add config */}
          <section className={`bg-white/90 backdrop-blur-xl rounded-2xl border border-blue-100/30 shadow-sm p-6 transition-opacity ${step >= 3 ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${step >= 3 ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white" : "bg-gray-100 text-gray-400"}`}>3</div>
              <h2 className="text-sm font-semibold text-[#0d1424]">Add to {APPS.find((a) => a.id === selectedApp)?.label}</h2>
            </div>

            <div className="space-y-3">
              <div className="rounded-lg border border-blue-100/40 bg-[#f7f9fd] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.14em] text-[#8b97ad] mb-1">Config file</div>
                <code className="text-[11px] text-[#3a5a8c] font-mono">{configPath(selectedApp)}</code>
              </div>

              <div className="text-[11px] text-[#556480]">
                {selectedApp === "codex"
                  ? "Add this to your Codex config file:"
                  : "Merge this into your config file (add the \"guardian\" entry inside \"mcpServers\"):"}
              </div>

              <div className="relative">
                <pre className="text-[11px] bg-[#f0f3f8] rounded-lg p-4 text-[#3a5a8c] overflow-x-auto font-mono leading-relaxed">
                  {configSnippet(selectedApp, token)}
                </pre>
                <button
                  onClick={() => copyToClipboard(configSnippet(selectedApp, token), "config")}
                  className="absolute top-2 right-2 px-2 py-1 rounded text-[10px] font-semibold bg-white/90 border border-blue-100/50 text-[#3a5a8c] hover:bg-white transition-colors"
                >
                  {copied === "config" ? "Copied" : "Copy"}
                </button>
              </div>

              <div className="text-[11px] text-[#7b8ba5]">
                After pasting, restart {APPS.find((a) => a.id === selectedApp)?.label} to load Guardian tools.
              </div>
            </div>
          </section>

          {/* Step 4: Verify */}
          <section className={`bg-white/90 backdrop-blur-xl rounded-2xl border border-blue-100/30 shadow-sm p-6 transition-opacity ${step >= 3 ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${step >= 3 ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white" : "bg-gray-100 text-gray-400"}`}>4</div>
              <h2 className="text-sm font-semibold text-[#0d1424]">Try it out</h2>
            </div>
            <div className="text-[11px] text-[#556480] space-y-2">
              <p>After restarting your app, try these prompts:</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {[
                  "What's my compliance status?",
                  "When is my next deadline?",
                  "Generate my Form 8843",
                  "Do I need to file FBAR?",
                ].map((prompt) => (
                  <div key={prompt} className="rounded-lg border border-blue-100/30 bg-[#f7f9fd] px-3 py-2">
                    <code className="text-[11px] text-[#3a5a8c]">&quot;{prompt}&quot;</code>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>

        {/* Available tools */}
        <div className="mt-12">
          <h2 className="text-sm font-semibold text-[#0d1424] mb-4">20 tools available</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {TOOLS.map((group) => (
              <div key={group.name} className="rounded-xl border border-blue-100/30 bg-white/60 p-4">
                <div className="text-xs font-semibold text-[#0d1424] mb-2">{group.name}</div>
                <div className="flex flex-wrap gap-1">
                  {group.items.map((t) => (
                    <span key={t} className={`text-[10px] px-2 py-0.5 rounded-full font-mono ${group.color}`}>{t}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Power users: local install */}
        <div className="mt-12 rounded-2xl border border-blue-100/20 bg-[#f7f9fd] p-6">
          <h2 className="text-sm font-semibold text-[#0d1424] mb-2">Power users: local install</h2>
          <p className="text-[11px] text-[#556480] mb-3">
            Install the Python package for additional tools (local document parsing, Gmail integration, RAG queries):
          </p>
          <pre className="text-[11px] bg-[#f0f3f8] rounded-lg p-3 text-[#3a5a8c] font-mono overflow-x-auto">pip install compliance-os[agent] && guardian-mcp install</pre>
        </div>
      </main>
    </div>
  );
}
