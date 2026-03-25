"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn, authHeaders, getUser, logout } from "@/lib/auth";

interface TimelineEvent {
  date: string;
  title: string;
  type: string;
  category: string | null;
  documents: { id: string; filename: string; doc_type: string; category: string }[];
  risks: { id: string; title: string; action: string; consequence: string; immigration_impact: boolean; severity: string }[];
}

interface UploadPrompt {
  doc_type: string;
  prompt: string;
  why: string;
  event_date?: string;
}

interface Stats {
  documents: number;
  risks: number;
  verified: number;
  next_deadline_days: number | null;
}

interface TimelineData {
  events: TimelineEvent[];
  findings: unknown[];
  advisories: { id: string; title: string; action: string; consequence: string }[];
  upload_prompts: UploadPrompt[];
}

const API = "http://localhost:8000/api/dashboard";

const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  immigration: { bg: "rgba(91,141,238,0.1)", text: "#3d6bc5", border: "rgba(91,141,238,0.12)" },
  tax: { bg: "rgba(16,185,129,0.1)", text: "#059669", border: "rgba(16,185,129,0.12)" },
  entity: { bg: "rgba(124,58,237,0.1)", text: "#7c3aed", border: "rgba(124,58,237,0.12)" },
};

export default function DashboardPage() {
  const router = useRouter();
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [uploadDocType, setUploadDocType] = useState("");
  const [showUploadPanel, setShowUploadPanel] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [view, setView] = useState<"timeline" | "documents">("timeline");
  const [documents, setDocuments] = useState<{ id: string; filename: string; doc_type: string; file_size: number; uploaded_at: string }[]>([]);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
      return;
    }
    Promise.all([
      fetch(`${API}/timeline`, { headers: authHeaders() }).then((r) => r.json()),
      fetch(`${API}/stats`, { headers: authHeaders() }).then((r) => r.json()),
      fetch(`${API}/documents`, { headers: authHeaders() }).then((r) => r.json()),
    ]).then(([tl, st, docs]) => {
      setTimeline(tl);
      setStats(st);
      setDocuments(docs);
      setLoading(false);
    });
  }, [router]);

  async function handleUpload(file: File, docType: string) {
    const form = new FormData();
    form.append("file", file);
    form.append("doc_type", docType);
    await fetch(`${API}/upload`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
    });
    // Refresh
    const [tl, st, docs] = await Promise.all([
      fetch(`${API}/timeline`, { headers: authHeaders() }).then((r) => r.json()),
      fetch(`${API}/stats`, { headers: authHeaders() }).then((r) => r.json()),
      fetch(`${API}/documents`, { headers: authHeaders() }).then((r) => r.json()),
    ]);
    setTimeline(tl);
    setStats(st);
    setDocuments(docs);
  }

  const user = getUser();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-[#5b8dee] border-t-transparent animate-spin" />
      </div>
    );
  }

  const DOT_STYLE: Record<string, string> = {
    milestone: "bg-gradient-to-br from-emerald-400 to-emerald-500",
    now: "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] shadow-[0_0_10px_rgba(91,141,238,0.3)]",
    deadline: "bg-gray-300",
    filing: "bg-gradient-to-br from-emerald-400 to-emerald-500",
  };

  return (
    <div className="min-h-screen">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-4 md:px-8 py-3 flex items-center justify-between bg-[#dce4f0]/60 backdrop-blur-2xl border-b border-blue-200/20">
        <div className="text-lg font-extrabold text-[#0d1424]">Guardian</div>
        <div className="flex items-center gap-2 md:gap-4">
          <span className="text-sm text-[#556480] hidden md:inline">{user?.email}</span>
          <button onClick={() => setShowUploadPanel(true)} className="px-3 md:px-4 py-2 rounded-lg bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-xs md:text-sm font-semibold">
            + Upload document
          </button>
          <button onClick={() => { logout(); router.push("/"); }} className="text-xs md:text-sm text-[#7b8ba5]">
            Sign out
          </button>
        </div>
      </nav>

      <div className="flex flex-col md:flex-row pt-14">
        {/* Sidebar — hidden on mobile, shown on md+ */}
        <div className="hidden md:block w-64 flex-shrink-0 p-5 bg-white/30 backdrop-blur-xl border-r border-white/50 min-h-screen">
          <div className="mb-7">
            <div className="text-[10px] font-bold uppercase tracking-widest text-[#7b8ba5] mb-2.5">Views</div>
            <button onClick={() => setView("timeline")} className={`w-full text-left text-sm px-3 py-2 rounded-lg mb-1 transition-all ${view === "timeline" ? "font-semibold text-[#3d6bc5] bg-[#5b8dee]/8" : "text-[#556480] hover:bg-white/40"}`}>Timeline</button>
            <button onClick={() => setView("documents")} className={`w-full text-left text-sm px-3 py-2 rounded-lg mb-1 transition-all ${view === "documents" ? "font-semibold text-[#3d6bc5] bg-[#5b8dee]/8" : "text-[#556480] hover:bg-white/40"}`}>
              All Documents
              <span className="ml-2 text-[11px] font-semibold px-2 py-0.5 rounded-md bg-[#5b8dee]/8 text-[#5b8dee]">{documents.length}</span>
            </button>
          </div>

          <div className="mb-7">
            <div className="text-[10px] font-bold uppercase tracking-widest text-[#7b8ba5] mb-2.5">Categories</div>
            {["immigration", "tax", "entity"].map((cat) => {
              const count = timeline?.events.filter((e) => e.category === cat).length || 0;
              const colors = CATEGORY_COLORS[cat];
              return (
                <div key={cat} className="flex items-center gap-2.5 px-3 py-2 text-sm text-[#556480] capitalize">
                  <span className="w-2 h-2 rounded-full" style={{ background: colors.text }} />
                  {cat}
                  <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-md" style={{ background: colors.bg, color: colors.text }}>{count}</span>
                </div>
              );
            })}
          </div>

          <div className="mb-7">
            <div className="text-[10px] font-bold uppercase tracking-widest text-[#7b8ba5] mb-2.5">Risks</div>
            <div className="flex items-center gap-2.5 px-3 py-2 text-sm text-[#556480]">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              Needs attention
              <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-md bg-red-50 text-red-500">{stats?.risks || 0}</span>
            </div>
            <div className="flex items-center gap-2.5 px-3 py-2 text-sm text-[#556480]">
              <span className="w-2 h-2 rounded-full bg-[#8e9ab5]" />
              Advisories
              <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-md bg-blue-50 text-[#5b8dee]">{timeline?.advisories.length || 0}</span>
            </div>
          </div>
        </div>

        {/* Main */}
        <div className="flex-1 p-4 md:p-8 max-w-[900px]">
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-8">
            {[
              { num: stats?.documents || 0, label: "Documents", color: "#0d1424" },
              { num: stats?.risks || 0, label: "Needs attention", color: "#f59e0b" },
              { num: stats?.verified || 0, label: "Verified fields", color: "#10b981" },
              { num: stats?.next_deadline_days != null ? `${stats.next_deadline_days}d` : "—", label: "Next deadline", color: "#5b8dee" },
            ].map((s) => (
              <div key={s.label} className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 p-4 md:p-5 shadow-[0_2px_12px_rgba(91,141,238,0.04)]">
                <div className="text-3xl font-bold" style={{ color: s.color }}>{s.num}</div>
                <div className="text-[11px] text-[#7b8ba5] mt-1">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Mobile view toggle */}
          <div className="flex md:hidden gap-2 mb-4">
            <button onClick={() => setView("timeline")} className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${view === "timeline" ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white" : "bg-white/50 text-[#556480]"}`}>Timeline</button>
            <button onClick={() => setView("documents")} className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${view === "documents" ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white" : "bg-white/50 text-[#556480]"}`}>Documents ({documents.length})</button>
          </div>

          {/* Documents View */}
          {view === "documents" && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-[#0d1424]">All Documents</h2>
                <button onClick={() => setShowUploadPanel(true)} className="text-[13px] font-medium text-[#5b8dee]">+ Upload</button>
              </div>
              {(() => {
                const grouped: Record<string, typeof documents> = {};
                for (const doc of documents) {
                  const cat = doc.doc_type === "i983" || doc.doc_type === "employment_letter" || doc.doc_type === "ead" || doc.doc_type === "i20" || doc.doc_type === "i797" || doc.doc_type === "i94"
                    ? "Immigration" : doc.doc_type === "tax_return" || doc.doc_type === "w2"
                    ? "Tax" : "Other";
                  if (!grouped[cat]) grouped[cat] = [];
                  grouped[cat].push(doc);
                }
                const DOC_LABELS: Record<string, string> = {
                  employment_letter: "Employment Letter", i983: "Form I-983", ead: "EAD Card", i20: "I-20",
                  i797: "I-797", i94: "I-94", tax_return: "Tax Return", w2: "W-2", other: "Other",
                };
                return Object.entries(grouped).map(([category, docs]) => (
                  <div key={category} className="mb-6">
                    <div className="text-[11px] font-semibold text-[#7b8ba5] uppercase tracking-widest mb-2">{category}</div>
                    <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 overflow-hidden">
                      {docs.map((doc, i) => (
                        <div key={doc.id} className={`flex items-center gap-3 px-5 py-3.5 ${i > 0 ? "border-t border-blue-50/40" : ""}`}>
                          <div className="w-8 h-8 rounded-lg bg-[#5b8dee]/6 flex items-center justify-center text-xs font-bold text-[#5b8dee]">
                            {(DOC_LABELS[doc.doc_type] || doc.doc_type).charAt(0)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-[13px] font-semibold text-[#0d1424] truncate">{doc.filename}</div>
                            <div className="text-[11px] text-[#7b8ba5]">
                              {DOC_LABELS[doc.doc_type] || doc.doc_type} · {doc.file_size ? `${Math.round(doc.file_size / 1024)}KB` : ""} · {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : ""}
                            </div>
                          </div>
                          <a
                            href={`http://localhost:8000/api/checks/_/documents/${doc.id}/download`}
                            className="text-[12px] font-medium text-[#5b8dee] hover:text-[#4a74d4] flex-shrink-0"
                            target="_blank"
                            rel="noreferrer"
                          >
                            View
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                ));
              })()}
              {documents.length === 0 && (
                <div className="text-center py-12">
                  <div className="text-[#8e9ab5] text-sm mb-3">No documents yet</div>
                  <button onClick={() => setShowUploadPanel(true)} className="text-[13px] font-medium text-[#5b8dee]">Upload your first document</button>
                </div>
              )}
            </div>
          )}

          {/* Timeline */}
          {view === "timeline" && (<><div className="relative pl-7">
            <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-gradient-to-b from-[#5b8dee] to-[#5b8dee]/10" />

            {timeline?.events.map((event, i) => (
              <div key={i} className="relative mb-6">
                <div className={`absolute -left-[18px] top-1.5 w-3.5 h-3.5 rounded-full border-[3px] border-white ${DOT_STYLE[event.type] || "bg-gray-300"}`} />

                <div className={`text-[11px] font-semibold tracking-wide mb-1 ${event.type === "now" ? "text-[#5b8dee]" : "text-[#8e9ab5]"}`}>
                  {event.type === "now" ? "TODAY" : event.date.toUpperCase()}
                </div>
                <div className={`text-[15px] font-semibold mb-2 ${event.type === "now" ? "text-[#0d1424]" : "text-[#0d1424]"}`}>
                  {event.title}
                </div>

                {/* Documents */}
                {event.documents.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-2">
                    {event.documents.map((doc) => {
                      const colors = CATEGORY_COLORS[doc.category] || CATEGORY_COLORS.immigration;
                      return (
                        <div key={doc.id} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/55 backdrop-blur border border-white/60 text-[12px] font-medium text-[#3d6bc5] shadow-sm cursor-pointer hover:bg-white/80 transition-all">
                          <span>📄</span>
                          {doc.filename}
                          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-md capitalize" style={{ background: colors.bg, color: colors.text, border: `1px solid ${colors.border}` }}>
                            {doc.category}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Risks */}
                {event.risks && event.risks.length > 0 && event.risks.map((risk) => (
                  <div key={risk.id} className="bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 px-5 py-4 mb-2 shadow-sm">
                    <div className="font-semibold text-[13px] text-[#0d1424] mb-1">{risk.title}</div>
                    <div className="text-[12px] text-[#556480] mb-2">{risk.action}</div>
                    <div className="flex gap-2">
                      <span className="text-[10px] px-2.5 py-0.5 rounded-full font-semibold" style={{ background: "rgba(245,158,11,0.12)", color: "#b45309", border: "1px solid rgba(245,158,11,0.15)" }}>
                        {risk.consequence}
                      </span>
                      {risk.immigration_impact && (
                        <span className="text-[10px] px-2.5 py-0.5 rounded-full font-semibold" style={{ background: "rgba(239,68,68,0.1)", color: "#dc2626", border: "1px solid rgba(239,68,68,0.12)" }}>
                          Immigration impact
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ))}

            {/* Upload Prompts */}
            {timeline?.upload_prompts.map((prompt, i) => (
              <div key={i} className="relative mb-6">
                <div className="absolute -left-[18px] top-1.5 w-3.5 h-3.5 rounded-full border-[3px] border-white bg-amber-400" />
                <div
                  onClick={() => { setUploadDocType(prompt.doc_type); fileRef.current?.click(); }}
                  className="px-5 py-4 rounded-2xl border border-dashed border-[#5b8dee]/20 bg-[#5b8dee]/4 cursor-pointer hover:bg-[#5b8dee]/8 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[#5b8dee]/8 flex items-center justify-center text-sm">📤</div>
                    <div>
                      <div className="text-[13px] font-semibold text-[#3d6bc5]">{prompt.prompt}</div>
                      <div className="text-[11px] text-[#7b8ba5] mt-0.5">{prompt.why}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Advisories — with upload action buttons */}
          {timeline && timeline.advisories.length > 0 && (
            <div className="mt-8">
              <div className="text-xs font-semibold text-[#7b8ba5] uppercase tracking-widest mb-3">Also worth checking</div>
              <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 overflow-hidden">
                {timeline.advisories.map((a, i) => (
                  <div key={a.id} className={`px-5 py-4 ${i > 0 ? "border-t border-blue-50/40" : ""}`}>
                    <div className="flex items-start gap-3">
                      <div className="flex-1 text-[13px]">
                        <span className="font-semibold text-[#3d6bc5]">{a.title}</span>
                        <span className="text-[#556480]"> — {a.action}</span>
                      </div>
                      <span className="text-[11px] font-semibold px-3 py-1 rounded-full flex-shrink-0" style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.1)" }}>
                        {a.consequence}
                      </span>
                    </div>
                    <button
                      onClick={() => { setUploadDocType(a.title.toLowerCase().replace(/[^a-z0-9]/g, "_")); setShowUploadPanel(true); }}
                      className="mt-2 text-[12px] font-medium text-[#5b8dee] hover:text-[#4a74d4] transition-colors"
                    >
                      Upload related document →
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
          </>)}

          {/* Hidden file input for timeline upload prompts */}
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            className="hidden"
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (f) {
                setUploading(true);
                setShowUploadPanel(false);
                await handleUpload(f, uploadDocType || "other");
                setUploading(false);
                setUploadDocType("");
              }
            }}
          />

          {/* Upload Panel Modal */}
          {showUploadPanel && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0d1424]/20 backdrop-blur-sm p-4">
              <div className="w-full max-w-md bg-white/80 backdrop-blur-xl rounded-2xl border border-white/60 p-6 shadow-[0_16px_64px_rgba(91,141,238,0.15)]">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold text-[#0d1424]">Upload a document</h2>
                  <button onClick={() => setShowUploadPanel(false)} className="text-[#7b8ba5] hover:text-[#0d1424] text-xl">&times;</button>
                </div>

                {/* Drop zone — upload first, classify optional */}
                <div
                  onClick={() => { if (!uploading) fileRef.current?.click(); }}
                  className={`flex flex-col items-center px-6 py-10 rounded-xl border-2 border-dashed transition-all cursor-pointer mb-5 ${
                    uploading ? "border-blue-300 bg-blue-50/30" : "border-blue-200/40 bg-white/50 hover:border-blue-300/60 hover:bg-white/70"
                  }`}
                >
                  {uploading ? (
                    <div className="text-sm text-[#5b8dee] font-medium">Uploading and analyzing...</div>
                  ) : (
                    <>
                      <div className="text-[15px] font-semibold text-[#0d1424] mb-1">Drop any document here</div>
                      <div className="text-xs text-[#8e9ab5]">PDF, JPG, or PNG — we&apos;ll figure out what it is</div>
                    </>
                  )}
                </div>

                {/* Optional: help us classify */}
                <div className="text-[11px] font-semibold text-[#7b8ba5] uppercase tracking-widest mb-2">Optional — helps improve accuracy</div>
                <div className="flex flex-wrap gap-1.5 mb-5">
                  {[
                    { type: "employment_letter", label: "Employment Letter" },
                    { type: "i983", label: "I-983" },
                    { type: "ead", label: "EAD Card" },
                    { type: "i20", label: "I-20" },
                    { type: "i797", label: "I-797" },
                    { type: "tax_return", label: "Tax Return" },
                    { type: "w2", label: "W-2" },
                  ].map((doc) => (
                    <button
                      key={doc.type}
                      onClick={() => setUploadDocType(uploadDocType === doc.type ? "" : doc.type)}
                      className={`px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all ${
                        uploadDocType === doc.type
                          ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-sm"
                          : "bg-white/60 border border-blue-100/30 text-[#3a5a8c] hover:bg-white/90"
                      }`}
                    >
                      {doc.label}
                    </button>
                  ))}
                </div>

                <p className="text-[11px] text-[#8e9ab5] text-center">
                  Your documents are stored securely and used only for compliance checking.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
