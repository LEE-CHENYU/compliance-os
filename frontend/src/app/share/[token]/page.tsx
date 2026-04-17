"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API_HOST =
  typeof window !== "undefined" && window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : "";

interface Slot {
  id: string;
  title: string;
  description: string;
  required: boolean;
  order: number;
  phase: string;
  status: "matched" | "missing" | "optional_missing";
  file: string | null;
  score: number;
}
interface Section { code: string; name: string; slots: Slot[]; }
interface KeyFact { label: string; value: string; }
interface TimelinePhase { name: string; period: string; detail: string; }
interface Issue { id: string; title: string; severity: string; summary: string; }
interface Summary {
  title: string;
  prepared_for: string;
  prepared_by: string;
  date: string;
  overview: string;
  key_facts: KeyFact[];
  timeline: TimelinePhase[];
  issues: Issue[];
  pending_items: string[];
  open_questions: string[];
}
interface ShareData {
  template_name: string;
  recipient: string;
  issuer: string;
  expires_at: number;
  files_scanned: number;
  coverage: Record<string, number>;
  missing_required: { id: string; title: string; section: string }[];
  missing_optional: { id: string; title: string; section: string }[];
  unmatched_files: string[];
  lineage_issues: string[];
  misplaced: { file: string; current: string; expected: string }[];
  sections: Section[];
  summary: Summary;
}

function StatusDot({ status, required }: { status: Slot["status"]; required: boolean }) {
  if (status === "matched") return <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />;
  if (status === "missing") return <span className="inline-block w-1.5 h-1.5 rounded-full bg-rose-500" />;
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${required ? "bg-amber-400" : "bg-slate-300"}`} />;
}

function SeverityBadge({ severity }: { severity: string }) {
  const style =
    severity === "critical"
      ? "bg-rose-100 text-rose-700 border-rose-200"
      : severity === "warning"
      ? "bg-amber-100 text-amber-700 border-amber-200"
      : "bg-blue-100 text-blue-700 border-blue-200";
  return <span className={`px-2 py-0.5 text-[10px] uppercase tracking-wider font-semibold rounded-full border ${style}`}>{severity}</span>;
}

export default function SharePage() {
  const params = useParams<{ token: string }>();
  const token = params?.token;
  const [data, setData] = useState<ShareData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<Slot | null>(null);

  useEffect(() => {
    if (!token) return;
    fetch(`${API_HOST}/api/share/${token}`)
      .then(async (r) => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(body.detail || `HTTP ${r.status}`);
        }
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message));
  }, [token]);

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#f0f4fa] via-white to-[#e8edf5] flex items-center justify-center p-6">
        <div className="max-w-md w-full rounded-2xl bg-white/90 backdrop-blur-xl border border-rose-100 shadow-sm p-8">
          <h1 className="text-base font-semibold text-[#0d1424] mb-2">Cannot open share link</h1>
          <p className="text-sm text-[#556480]">{error}</p>
          <p className="text-xs text-[#8b97ad] mt-4">Ask the sender to issue a new link.</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#f0f4fa] via-white to-[#e8edf5] flex items-center justify-center">
        <div className="text-sm text-[#556480]">Loading case package…</div>
      </div>
    );
  }

  const { summary, sections, coverage } = data;
  const overallReq = sections.reduce((acc, s) => acc + s.slots.filter((sl) => sl.required).length, 0);
  const overallHit = sections.reduce((acc, s) => acc + s.slots.filter((sl) => sl.required && sl.status === "matched").length, 0);
  const overallPct = overallReq ? Math.round((100 * overallHit) / overallReq) : 0;
  const expiresDate = new Date((data.expires_at || 0) * 1000);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4fa] via-white to-[#e8edf5]">
      {/* Header */}
      <header className="border-b border-blue-100/30 bg-white/80 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
          <a href="/" className="flex items-center gap-2.5 group" aria-label="Guardian home">
            <div style={{width:22, height:22, display:'flex', flexDirection:'column', gap:2.5, transform:'perspective(200px) rotateX(-8deg) rotateY(12deg)'}} className="group-hover:opacity-90 transition-opacity">
              <div style={{height:4.5, background:'linear-gradient(135deg, #5b8dee, #4a74d4)', borderRadius:1, width:22, transform:'translateX(2px)'}} />
              <div style={{height:4.5, background:'linear-gradient(135deg, #5b8dee, #4a74d4)', borderRadius:1, width:22, transform:'translateX(-1px)'}} />
              <div style={{height:4.5, background:'linear-gradient(135deg, #5b8dee, #4a74d4)', borderRadius:1, width:22, transform:'translateX(3px)'}} />
            </div>
            <span className="text-sm font-bold tracking-tight text-[#0d1424]">Guardian</span>
            <span className="text-sm text-[#8b97ad] font-normal hidden sm:inline">· Data Room</span>
          </a>
          <div className="flex items-center gap-4">
            <a
              href={`${API_HOST}/api/share/${token}/download`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white hover:shadow-md transition-shadow"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Download all
            </a>
            <div className="text-[11px] text-[#8b97ad] hidden sm:block">
              Read-only · Expires {expiresDate.toLocaleDateString()}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10 space-y-8">
        {/* Cover */}
        <section className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-8">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#8b97ad] mb-2">{data.template_name}</div>
              <h1 className="text-2xl font-bold text-[#0d1424] mb-3">{summary.title || data.template_name}</h1>
              <div className="flex flex-wrap gap-4 text-xs text-[#556480]">
                {summary.prepared_for && <div><span className="text-[#8b97ad]">Prepared for:</span> <span className="font-medium text-[#3a5a8c]">{summary.prepared_for}</span></div>}
                {summary.prepared_by && <div><span className="text-[#8b97ad]">Prepared by:</span> <span className="font-medium">{summary.prepared_by}</span></div>}
                {summary.date && <div><span className="text-[#8b97ad]">Date:</span> <span className="font-medium">{summary.date}</span></div>}
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-[#3a5a8c]">{overallPct}%</div>
              <div className="text-[10px] uppercase tracking-wider text-[#8b97ad]">
                {overallHit} of {overallReq} required
              </div>
              <div className="text-[10px] text-[#8b97ad] mt-1">{data.files_scanned} files in package</div>
            </div>
          </div>
          {summary.overview && (
            <p className="text-sm text-[#556480] mt-6 leading-relaxed">{summary.overview}</p>
          )}
        </section>

        {/* Coverage strip */}
        <section className="grid grid-cols-7 gap-2">
          {sections.map((s) => {
            const pct = Math.round((coverage[s.code] || 0) * 100);
            return (
              <a key={s.code} href={`#sec-${s.code}`} className="rounded-xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-3 hover:shadow-md transition-shadow">
                <div className="text-[10px] uppercase tracking-wider text-[#8b97ad] mb-1">{s.code}</div>
                <div className="text-[11px] font-medium text-[#0d1424] mb-2 truncate">{s.name}</div>
                <div className="flex items-center justify-between">
                  <div className="text-base font-bold text-[#3a5a8c]">{pct}%</div>
                  <div className="text-[10px] text-[#8b97ad]">{s.slots.filter(sl => sl.status === "matched").length}/{s.slots.filter(sl => sl.required).length}</div>
                </div>
              </a>
            );
          })}
        </section>

        {/* Key facts */}
        {summary.key_facts.length > 0 && (
          <section className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6">
            <h2 className="text-sm font-semibold text-[#0d1424] mb-4">Key facts</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-3">
              {summary.key_facts.map((f) => (
                <div key={f.label}>
                  <div className="text-[10px] uppercase tracking-wider text-[#8b97ad] mb-0.5">{f.label}</div>
                  <div className="text-xs text-[#0d1424] font-medium">{f.value}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Timeline */}
        {summary.timeline.length > 0 && (
          <section className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6">
            <h2 className="text-sm font-semibold text-[#0d1424] mb-4">Status lineage</h2>
            <ol className="relative border-l border-blue-100 ml-2 space-y-4">
              {summary.timeline.map((p, i) => (
                <li key={i} className="ml-4 pl-2">
                  <div className="absolute -left-[5px] w-2.5 h-2.5 bg-white border-2 border-[#5b8dee] rounded-full" />
                  <div className="text-xs font-semibold text-[#0d1424]">{p.name}</div>
                  <div className="text-[11px] text-[#8b97ad]">{p.period}</div>
                </li>
              ))}
            </ol>
          </section>
        )}

        {/* Known issues */}
        {summary.issues.length > 0 && (
          <section className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6">
            <h2 className="text-sm font-semibold text-[#0d1424] mb-4">Known issues — proactive disclosure</h2>
            <ul className="space-y-2">
              {summary.issues.map((iss) => (
                <li key={iss.id} className="flex items-start gap-3 py-2 border-b border-blue-50 last:border-0">
                  <SeverityBadge severity={iss.severity} />
                  <span className="text-xs text-[#0d1424] flex-1">{iss.title}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Sections */}
        {sections.map((s) => (
          <section key={s.code} id={`sec-${s.code}`} className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-[#0d1424]">
                <span className="text-[#8b97ad] mr-2">{s.code}</span>
                {s.name}
              </h2>
              <div className="text-[11px] text-[#8b97ad]">
                {s.slots.filter(sl => sl.status === "matched").length} / {s.slots.filter(sl => sl.required).length} required
              </div>
            </div>
            <div className="divide-y divide-blue-50/60">
              {s.slots.map((slot) => (
                <button
                  key={slot.id}
                  onClick={() => slot.file && setPreview(slot)}
                  disabled={!slot.file}
                  className={`w-full text-left py-3 px-2 -mx-2 rounded-lg flex items-start gap-3 transition-colors ${
                    slot.file ? "hover:bg-blue-50/40 cursor-pointer" : "cursor-default opacity-80"
                  }`}
                >
                  <StatusDot status={slot.status} required={slot.required} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2">
                      <span className="text-[11px] font-mono text-[#8b97ad]">{slot.id}</span>
                      <span className="text-xs font-medium text-[#0d1424]">{slot.title}</span>
                      {!slot.required && (
                        <span className="text-[9px] uppercase tracking-wider text-[#a6b0c5]">optional</span>
                      )}
                    </div>
                    {slot.description && (
                      <div className="text-[11px] text-[#8b97ad] mt-0.5">{slot.description}</div>
                    )}
                    {slot.file ? (
                      <div className="text-[11px] text-[#3a5a8c] mt-1 truncate">{slot.file}</div>
                    ) : (
                      <div className="text-[11px] text-[#b0748f] mt-1">
                        {slot.required ? "Missing — required" : "Not included"}
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </section>
        ))}

        {/* Pending — computed from current matcher state, not the brief */}
        {(() => {
          const pending = [...data.missing_required, ...data.missing_optional];
          if (pending.length === 0) return null;
          return (
            <section className="rounded-2xl bg-white/90 backdrop-blur-xl border border-blue-100/30 shadow-sm p-6">
              <h2 className="text-sm font-semibold text-[#0d1424] mb-3">Pending items</h2>
              <ul className="space-y-1.5">
                {pending.map((p) => (
                  <li key={p.id} className="text-xs text-[#556480] flex items-start gap-2">
                    <span className={`mt-1 ${data.missing_required.some(m => m.id === p.id) ? "text-rose-500" : "text-amber-500"}`}>•</span>
                    <span className="font-mono text-[10px] text-[#8b97ad] mr-2">{p.id}</span>
                    <span>{p.title}</span>
                  </li>
                ))}
              </ul>
            </section>
          );
        })()}

        <footer className="text-center text-[10px] text-[#a6b0c5] py-6">
          Generated by Guardian · {data.recipient && `Recipient: ${data.recipient} · `}Link expires {expiresDate.toLocaleDateString()}
        </footer>
      </main>

      {/* File preview drawer */}
      {preview && (
        <div className="fixed inset-0 bg-[#0d1424]/40 backdrop-blur-sm z-20 flex items-stretch justify-end" onClick={() => setPreview(null)}>
          <div className="bg-white w-full md:w-2/3 lg:w-1/2 h-full shadow-2xl flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 border-b border-blue-100 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-mono text-[#8b97ad]">{preview.id}</div>
                <div className="text-sm font-semibold text-[#0d1424]">{preview.title}</div>
              </div>
              <button onClick={() => setPreview(null)} className="text-sm text-[#8b97ad] hover:text-[#0d1424] px-2">✕</button>
            </div>
            <iframe
              title={preview.title}
              src={`${API_HOST}/api/share/${token}/file/${preview.id}`}
              className="flex-1 w-full"
            />
          </div>
        </div>
      )}
    </div>
  );
}
