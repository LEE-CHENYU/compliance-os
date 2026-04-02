"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  triggerExtraction,
  triggerCompare,
  triggerEvaluate,
  generateFollowups,
  answerFollowup,
  getSnapshot,
  type Comparison,
  type Followup,
  type Snapshot,
} from "@/lib/api-v2";
import AuthModal from "@/components/auth/AuthModal";
import { useRouter } from "next/navigation";

export default function ReviewPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-[#8e9ab5]">Loading...</div>}>
      <ReviewFlow />
    </Suspense>
  );
}

type Phase = "extracting" | "comparing" | "followup" | "snapshot";

function ReviewFlow() {
  const params = useSearchParams();
  const checkId = params.get("id") || "";
  const [phase, setPhase] = useState<Phase>("extracting");
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [followups, setFollowups] = useState<Followup[]>([]);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Phase 1: Extract → Compare → Generate followups
  useEffect(() => {
    if (!checkId || phase !== "extracting") return;
    (async () => {
      try {
        await triggerExtraction(checkId);
        setPhase("comparing");
        const comps = await triggerCompare(checkId);
        setComparisons(comps);

        const fups = await generateFollowups(checkId);
        setFollowups(fups);

        if (fups.length > 0) {
          setPhase("followup");
        } else {
          // No mismatches — go straight to snapshot
          await triggerEvaluate(checkId);
          const snap = await getSnapshot(checkId);
          setSnapshot(snap);
          setPhase("snapshot");
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Something went wrong during extraction");
      }
    })();
  }, [checkId, phase]);

  const handleFollowupDone = useCallback(async () => {
    await triggerEvaluate(checkId);
    const snap = await getSnapshot(checkId);
    setSnapshot(snap);
    setPhase("snapshot");
  }, [checkId]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <div className="text-2xl mb-3">⚠️</div>
          <h2 className="text-xl font-bold mb-2">Something went wrong</h2>
          <p className="text-sm text-[#556480]">{error}</p>
        </div>
      </div>
    );
  }

  if (phase === "extracting" || phase === "comparing") {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="bg-white/50 backdrop-blur-xl rounded-3xl border border-white/60 shadow-[0_8px_40px_rgba(91,141,238,0.08)] px-16 py-14 text-center max-w-md">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#5b8dee]/10 to-[#4a74d4]/5 flex items-center justify-center mx-auto mb-6">
            <div className="w-8 h-8 rounded-full border-2 border-[#5b8dee] border-t-transparent animate-spin" />
          </div>
          <h2 className="text-xl font-bold text-[#0d1424] mb-2">
            {phase === "extracting" ? "Extracting fields from your documents..." : "Comparing fields..."}
          </h2>
          <p className="text-sm text-[#556480]">This usually takes about 15 seconds.</p>
        </div>
      </div>
    );
  }

  if (phase === "followup") {
    return (
      <FollowupView
        checkId={checkId}
        comparisons={comparisons}
        followups={followups}
        setFollowups={setFollowups}
        onDone={handleFollowupDone}
      />
    );
  }

  if (phase === "snapshot" && snapshot) {
    return <SnapshotView snapshot={snapshot} />;
  }

  return null;
}

// --- Extraction Grid (shown above followups) ---
function ExtractionGrid({ comparisons }: { comparisons: Comparison[] }) {
  const STATUS_ICON: Record<string, string> = {
    match: "✓",
    mismatch: "⚠️",
    needs_review: "⚡",
  };
  const STATUS_COLOR: Record<string, string> = {
    match: "text-green-600",
    mismatch: "text-amber-600",
    needs_review: "text-blue-500",
  };

  return (
    <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 overflow-hidden mb-8 shadow-[0_4px_32px_rgba(91,141,238,0.05)]">
      <div className="grid grid-cols-4 text-xs font-semibold text-[#7b8ba5] uppercase tracking-wider bg-white/30 backdrop-blur">
        <div className="px-5 py-3.5">Field</div>
        <div className="px-5 py-3.5">I-983</div>
        <div className="px-5 py-3.5">Employment Letter</div>
        <div className="px-5 py-3.5">Status</div>
      </div>
      {comparisons.map((c) => (
        <div key={c.id} className={`grid grid-cols-4 text-sm border-t border-white/40 ${c.status === "mismatch" ? "bg-amber-50/20" : c.status === "needs_review" ? "bg-blue-50/15" : ""}`}>
          <div className="px-5 py-3.5 font-medium text-[#3a5a8c] capitalize">{c.field_name.replace(/_/g, " ")}</div>
          <div className="px-5 py-3.5 text-[#0d1424] text-[13px]">{c.value_a || <span className="text-[#b0bdd0] italic">—</span>}</div>
          <div className="px-5 py-3.5 text-[#0d1424] text-[13px]">{c.value_b || <span className="text-[#b0bdd0] italic">—</span>}</div>
          <div className={`px-5 py-3.5 font-medium text-[13px] ${STATUS_COLOR[c.status]}`}>
            {STATUS_ICON[c.status]} {c.status === "match" ? "Match" : c.status === "mismatch" ? "Mismatch" : "Review"}
          </div>
        </div>
      ))}
    </div>
  );
}

// --- Follow-up Panel ---
function FollowupView({
  checkId,
  comparisons,
  followups,
  setFollowups,
  onDone,
}: {
  checkId: string;
  comparisons: Comparison[];
  followups: Followup[];
  setFollowups: (f: Followup[]) => void;
  onDone: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);

  const allAnswered = followups.every((f) => f.answer);

  async function handleAnswer(fup: Followup, answer: string) {
    const updated = await answerFollowup(checkId, fup.id, answer);
    setFollowups(followups.map((f) => (f.id === fup.id ? updated : f)));
  }

  async function handleDone() {
    setSubmitting(true);
    await onDone();
  }

  const mismatches = comparisons.filter((c) => c.status !== "match");

  return (
    <div className="min-h-screen px-6 py-20 max-w-3xl mx-auto">
      <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
        Here&apos;s what we found
      </h1>
      <p className="text-[15px] text-[#556480] mb-8">
        {mismatches.length} field{mismatches.length !== 1 ? "s" : ""} need attention. Answer a few questions to complete the check.
      </p>

      <ExtractionGrid comparisons={comparisons} />

      <h2 className="text-xl font-bold text-[#0d1424] mb-4">Quick questions</h2>
      <div className="flex flex-col gap-3 mb-8">
        {followups.map((fup) => (
          <div
            key={fup.id}
            className="bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 p-6 shadow-[0_4px_24px_rgba(91,141,238,0.06)] hover:shadow-[0_8px_32px_rgba(91,141,238,0.1)] transition-all"
          >
            <p className="font-medium text-[14px] text-[#0d1424] mb-4 leading-relaxed">{fup.question_text}</p>
            <div className="flex flex-wrap gap-2">
              {(fup.chips || []).map((chip) => (
                <button
                  key={chip}
                  onClick={() => handleAnswer(fup, chip)}
                  className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    fup.answer === chip
                      ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_2px_12px_rgba(74,116,212,0.3)]"
                      : "bg-white/70 backdrop-blur border border-blue-100/30 text-[#3a5a8c] hover:bg-white/90 hover:border-blue-200/40 hover:shadow-sm"
                  }`}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={handleDone}
        disabled={!allAnswered || submitting}
        className={`w-full py-4 rounded-xl font-semibold text-[15px] transition-all ${
          allAnswered
            ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_4px_16px_rgba(74,116,212,0.3)]"
            : "bg-gray-200 text-gray-400 cursor-not-allowed"
        }`}
      >
        {submitting ? "Analyzing..." : "See my results"}
      </button>
    </div>
  );
}

// --- Case Snapshot ---
function SnapshotView({ snapshot }: { snapshot: Snapshot }) {
  const router = useRouter();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const { comparisons, findings, advisories } = snapshot;
  const issues = findings.filter((f) => f.severity !== "info");
  const goods = comparisons.filter((c) => c.status === "match");

  const startDate = snapshot.extractions?.i983?.find((f) => f.field_name === "start_date")?.field_value;
  const endDate = snapshot.extractions?.i983?.find((f) => f.field_name === "end_date")?.field_value;

  return (
    <div className="min-h-screen px-6 py-20 max-w-3xl mx-auto">
      <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
        Your Student Check
      </h1>
      <p className="text-[15px] text-[#556480] mb-8">
        Based on your I-20 and uploaded documents
      </p>

      {/* Timeline */}
      <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 p-7 mb-6 shadow-[0_4px_24px_rgba(91,141,238,0.06)]">
        <h2 className="text-xs font-semibold text-[#7b8ba5] uppercase tracking-widest mb-5">Timeline</h2>
        <div className="relative ml-4">
          {/* Vertical line */}
          <div className="absolute left-[7px] top-2 bottom-2 w-[2px] bg-gradient-to-b from-emerald-300 via-[#5b8dee] to-gray-200" />

          <div className="space-y-0">
            {startDate && (
              <div className="relative flex items-start gap-5 pb-8">
                <div className="relative z-10 mt-0.5 w-4 h-4 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-500 border-[3px] border-white shadow-sm flex-shrink-0" />
                <div>
                  <div className="text-[11px] font-medium text-[#8e9ab5] tracking-wide">{startDate}</div>
                  <div className="text-[15px] font-semibold text-[#0d1424]">STEM OPT started</div>
                </div>
              </div>
            )}
            <div className="relative flex items-start gap-5 pb-8">
              <div className="relative z-10 mt-0.5 w-4 h-4 rounded-full bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] border-[3px] border-white shadow-[0_0_8px_rgba(91,141,238,0.3)] flex-shrink-0" />
              <div>
                <div className="text-[11px] font-semibold text-[#5b8dee] tracking-wide">TODAY</div>
                <div className="text-[15px] font-semibold text-[#0d1424]">{new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}</div>
              </div>
            </div>
            {endDate && (
              <div className="relative flex items-start gap-5">
                <div className="relative z-10 mt-0.5 w-4 h-4 rounded-full bg-gray-200 border-[3px] border-white flex-shrink-0" />
                <div>
                  <div className="text-[11px] font-medium text-[#8e9ab5] tracking-wide">{endDate}</div>
                  <div className="text-[15px] text-[#556480]">STEM OPT ends</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Findings */}
      {issues.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xs font-semibold text-[#c0392b] uppercase tracking-widest mb-3 flex items-center gap-2">
            Needs Attention ({issues.length})
          </h2>
          <div className="flex flex-col gap-3">
            {issues.map((f) => (
              <div key={f.id} className="bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 px-6 py-5 shadow-[0_4px_24px_rgba(91,141,238,0.05)]">
                <div className="font-semibold text-[15px] text-[#0d1424] mb-1.5">{f.title}</div>
                <div className="text-[13px] text-[#556480] leading-relaxed mb-3">{f.action}</div>
                <div className="flex flex-wrap gap-2">
                  <span className="text-[11px] px-3 py-1 rounded-full font-semibold backdrop-blur-sm"
                    style={{ background: 'rgba(245,158,11,0.12)', color: '#b45309', border: '1px solid rgba(245,158,11,0.15)' }}>
                    {f.consequence}
                  </span>
                  {f.immigration_impact && (
                    <span className="text-[11px] px-3 py-1 rounded-full font-semibold backdrop-blur-sm"
                      style={{ background: 'rgba(239,68,68,0.1)', color: '#dc2626', border: '1px solid rgba(239,68,68,0.12)' }}>
                      Immigration impact
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Looks good */}
      {goods.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xs font-semibold text-emerald-600 uppercase tracking-widest mb-3">
            Looks Good ({goods.length})
          </h2>
          <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 px-6 py-5 shadow-[0_2px_12px_rgba(91,141,238,0.04)]">
            <div className="flex flex-wrap gap-2">
              {goods.map((g) => (
                <span key={g.id} className="text-[12px] px-3.5 py-1.5 rounded-full font-semibold backdrop-blur-sm capitalize"
                  style={{ background: 'rgba(16,185,129,0.1)', color: '#059669', border: '1px solid rgba(16,185,129,0.12)' }}>
                  {g.field_name.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Advisories */}
      {advisories.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xs font-semibold text-[#7b8ba5] uppercase tracking-widest mb-3">
            Worth looking into
          </h2>
          <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 shadow-[0_2px_12px_rgba(91,141,238,0.04)] overflow-hidden">
            {advisories.map((a, i) => (
              <div key={a.id} className={`flex items-center gap-3 px-6 py-4 ${i > 0 ? 'border-t border-blue-50/40' : ''}`}>
                <div className="flex-1 text-[13px]">
                  <span className="font-semibold text-[#3d6bc5]">{a.title}</span>
                  <span className="text-[#556480]"> — {a.action}</span>
                </div>
                <span className="text-[11px] font-semibold whitespace-nowrap px-3 py-1 rounded-full backdrop-blur-sm"
                  style={{ background: 'rgba(239,68,68,0.08)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.1)' }}>
                  {a.consequence}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Save CTA */}
      <div className="text-center pt-8">
        <button
          onClick={() => setShowAuthModal(true)}
          className="px-10 py-4 rounded-2xl bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white font-semibold text-[15px] shadow-[0_4px_16px_rgba(74,116,212,0.3)] hover:shadow-[0_8px_28px_rgba(74,116,212,0.4)] hover:-translate-y-0.5 transition-all cursor-pointer"
        >
          Save to my data room
        </button>
        <p className="text-xs text-[#8e9ab5] mt-3">Create an account to save to your personal data room</p>
      </div>

      {showAuthModal && (
        <AuthModal
          checkId={snapshot.check.id}
          onSuccess={() => router.push("/dashboard")}
        />
      )}
    </div>
  );
}
