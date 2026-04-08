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

export const dynamic = "force-dynamic";

export default function EntityReviewPage() {
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
          await triggerEvaluate(checkId);
          const snap = await getSnapshot(checkId);
          setSnapshot(snap);
          setPhase("snapshot");
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Something went wrong");
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
        <div className="bg-white/50 backdrop-blur-xl rounded-3xl border border-white/60 shadow-lg px-16 py-14 text-center max-w-md">
          <div className="text-2xl mb-3">&#9888;&#65039;</div>
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
            {phase === "extracting" ? "Extracting fields from your tax return..." : "Checking against your answers..."}
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

function ExtractionGrid({ comparisons }: { comparisons: Comparison[] }) {
  const STATUS_ICON: Record<string, string> = { match: "\u2713", mismatch: "\u26A0\uFE0F", needs_review: "\u26A1" };
  const STATUS_COLOR: Record<string, string> = { match: "text-green-600", mismatch: "text-amber-600", needs_review: "text-blue-500" };

  return (
    <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 overflow-hidden mb-8 shadow-[0_4px_32px_rgba(91,141,238,0.05)]">
      <div className="grid grid-cols-4 text-xs font-semibold text-[#7b8ba5] uppercase tracking-wider bg-white/30 backdrop-blur">
        <div className="px-5 py-3.5">Field</div>
        <div className="px-5 py-3.5">Your Answers</div>
        <div className="px-5 py-3.5">Tax Return</div>
        <div className="px-5 py-3.5">Status</div>
      </div>
      {comparisons.map((c) => (
        <div key={c.id} className={`grid grid-cols-4 text-sm border-t border-white/40 ${c.status === "mismatch" ? "bg-amber-50/20" : ""}`}>
          <div className="px-5 py-3.5 font-medium text-[#3a5a8c] capitalize">{c.field_name.replace(/_/g, " ")}</div>
          <div className="px-5 py-3.5 text-[#0d1424] text-[13px]">{c.value_a || <span className="text-[#b0bdd0] italic">&mdash;</span>}</div>
          <div className="px-5 py-3.5 text-[#0d1424] text-[13px]">{c.value_b || <span className="text-[#b0bdd0] italic">&mdash;</span>}</div>
          <div className={`px-5 py-3.5 font-medium text-[13px] ${STATUS_COLOR[c.status]}`}>
            {STATUS_ICON[c.status]} {c.status === "match" ? "Match" : c.status === "mismatch" ? "Mismatch" : "Review"}
          </div>
        </div>
      ))}
    </div>
  );
}

function FollowupView({ checkId, comparisons, followups, setFollowups, onDone }: {
  checkId: string; comparisons: Comparison[]; followups: Followup[];
  setFollowups: (f: Followup[]) => void; onDone: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const allAnswered = followups.every((f) => f.answer);
  const mismatches = comparisons.filter((c) => c.status !== "match");

  async function handleAnswer(fup: Followup, answer: string) {
    const updated = await answerFollowup(checkId, fup.id, answer);
    setFollowups(followups.map((f) => (f.id === fup.id ? updated : f)));
  }

  return (
    <div className="min-h-screen px-6 py-20 max-w-3xl mx-auto">
      <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">Here&apos;s what we found</h1>
      <p className="text-[15px] text-[#556480] mb-8">
        {mismatches.length} item{mismatches.length !== 1 ? "s" : ""} need attention.
      </p>
      <ExtractionGrid comparisons={comparisons} />
      <h2 className="text-xl font-bold text-[#0d1424] mb-4">Quick questions</h2>
      <div className="flex flex-col gap-3 mb-8">
        {followups.map((fup) => (
          <div key={fup.id} className="bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 p-6 shadow-[0_4px_24px_rgba(91,141,238,0.06)]">
            <p className="font-medium text-[14px] text-[#0d1424] mb-4 leading-relaxed">{fup.question_text}</p>
            <div className="flex flex-wrap gap-2">
              {(fup.chips || []).map((chip) => (
                <button key={chip} onClick={() => handleAnswer(fup, chip)}
                  className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    fup.answer === chip
                      ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_2px_12px_rgba(74,116,212,0.3)]"
                      : "bg-white/70 backdrop-blur border border-blue-100/30 text-[#3a5a8c] hover:bg-white/90"
                  }`}>
                  {chip}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
      <button onClick={async () => { setSubmitting(true); await onDone(); }} disabled={!allAnswered || submitting}
        className={`w-full py-4 rounded-xl font-semibold text-[15px] transition-all ${
          allAnswered ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_4px_16px_rgba(74,116,212,0.3)]" : "bg-gray-200 text-gray-400 cursor-not-allowed"
        }`}>
        {submitting ? "Analyzing..." : "See my results"}
      </button>
    </div>
  );
}

function SnapshotView({ snapshot }: { snapshot: Snapshot }) {
  const router = useRouter();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const { comparisons, findings, advisories } = snapshot;
  const issues = findings.filter((f) => f.severity !== "info");
  const goods = comparisons.filter((c) => c.status === "match");

  return (
    <div className="min-h-screen px-6 py-20 max-w-3xl mx-auto">
      <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">Your Entity Check</h1>
      <p className="text-[15px] text-[#556480] mb-8">Based on your answers and tax return</p>

      {issues.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xs font-semibold text-[#c0392b] uppercase tracking-widest mb-3">Needs Attention ({issues.length})</h2>
          <div className="flex flex-col gap-3">
            {issues.map((f) => (
              <div key={f.id} className="bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 px-6 py-5 shadow-[0_4px_24px_rgba(91,141,238,0.05)]">
                <div className="font-semibold text-[15px] text-[#0d1424] mb-1.5">{f.title}</div>
                <div className="text-[13px] text-[#556480] leading-relaxed mb-3">{f.action}</div>
                <div className="flex flex-wrap gap-2">
                  <span className="text-[11px] px-3 py-1 rounded-full font-semibold backdrop-blur-sm"
                    style={{ background: f.severity === "critical" ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.12)', color: f.severity === "critical" ? '#dc2626' : '#b45309', border: `1px solid ${f.severity === "critical" ? 'rgba(239,68,68,0.12)' : 'rgba(245,158,11,0.15)'}` }}>
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

      {goods.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xs font-semibold text-emerald-600 uppercase tracking-widest mb-3">Looks Good ({goods.length})</h2>
          <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 px-6 py-5">
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

      {advisories.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xs font-semibold text-[#7b8ba5] uppercase tracking-widest mb-3">Worth looking into</h2>
          <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 overflow-hidden">
            {advisories.map((a, i) => (
              <div key={a.id} className={`flex items-center gap-3 px-6 py-4 ${i > 0 ? 'border-t border-blue-50/40' : ''}`}>
                <div className="flex-1 text-[13px]">
                  <span className="font-semibold text-[#3d6bc5]">{a.title}</span>
                  <span className="text-[#556480]"> &mdash; {a.action}</span>
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
