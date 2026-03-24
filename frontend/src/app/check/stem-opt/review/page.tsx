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
        <div className="text-center">
          <div className="w-12 h-12 rounded-full border-2 border-[#5b8dee] border-t-transparent animate-spin mx-auto mb-6" />
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
    <div className="bg-white/60 backdrop-blur rounded-2xl border border-white/70 overflow-hidden mb-8">
      <div className="grid grid-cols-4 text-xs font-semibold text-[#7b8ba5] uppercase tracking-wider border-b border-blue-100/20">
        <div className="px-5 py-3">Field</div>
        <div className="px-5 py-3">I-983</div>
        <div className="px-5 py-3">Employment Letter</div>
        <div className="px-5 py-3">Status</div>
      </div>
      {comparisons.map((c) => (
        <div key={c.id} className={`grid grid-cols-4 text-sm border-b border-blue-50/30 ${c.status === "mismatch" ? "bg-amber-50/30" : ""}`}>
          <div className="px-5 py-3 font-medium text-[#3a5a8c] capitalize">{c.field_name.replace(/_/g, " ")}</div>
          <div className="px-5 py-3 text-[#0d1424]">{c.value_a || <span className="text-[#b0bdd0] italic">—</span>}</div>
          <div className="px-5 py-3 text-[#0d1424]">{c.value_b || <span className="text-[#b0bdd0] italic">—</span>}</div>
          <div className={`px-5 py-3 font-medium ${STATUS_COLOR[c.status]}`}>
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
      <div className="flex flex-col gap-4 mb-8">
        {followups.map((fup) => (
          <div key={fup.id} className="bg-white/60 backdrop-blur rounded-xl border border-white/70 p-5 border-l-4 border-l-[#5b8dee]">
            <p className="font-medium text-[14px] text-[#0d1424] mb-3">{fup.question_text}</p>
            <div className="flex flex-wrap gap-2">
              {(fup.chips || []).map((chip) => (
                <button
                  key={chip}
                  onClick={() => handleAnswer(fup, chip)}
                  className={`px-4 py-2 rounded-full text-sm transition-all ${
                    fup.answer === chip
                      ? "bg-[#5b8dee] text-white shadow-sm"
                      : "bg-blue-50/60 text-[#3a5a8c] hover:bg-blue-100/60"
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
  const { comparisons, findings, advisories } = snapshot;
  const issues = findings.filter((f) => f.severity !== "info");
  const goods = comparisons.filter((c) => c.status === "match");

  // Extract dates for timeline
  const startDate = snapshot.extractions?.i983?.find((f) => f.field_name === "start_date")?.field_value;
  const endDate = snapshot.extractions?.i983?.find((f) => f.field_name === "end_date")?.field_value;

  return (
    <div className="min-h-screen px-6 py-20 max-w-3xl mx-auto">
      <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
        Your STEM OPT Check
      </h1>
      <p className="text-sm text-[#556480] mb-8">
        Based on your I-983 and employment letter
      </p>

      {/* Timeline */}
      <div className="bg-white/60 backdrop-blur rounded-2xl border border-white/70 p-6 mb-6">
        <h2 className="text-sm font-semibold text-[#7b8ba5] uppercase tracking-wider mb-4">Timeline</h2>
        <div className="relative pl-6 border-l-2 border-blue-200/40 space-y-5">
          {startDate && (
            <div className="relative">
              <div className="absolute -left-[25px] top-1 w-3 h-3 rounded-full bg-green-400 border-2 border-white" />
              <div className="text-xs text-[#8e9ab5]">{startDate}</div>
              <div className="text-sm font-medium">STEM OPT started ✓</div>
            </div>
          )}
          <div className="relative">
            <div className="absolute -left-[25px] top-1 w-3 h-3 rounded-full bg-[#5b8dee] border-2 border-white" />
            <div className="text-xs text-[#8e9ab5]">Today</div>
            <div className="text-sm font-medium">{new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" })}</div>
          </div>
          {endDate && (
            <div className="relative">
              <div className="absolute -left-[25px] top-1 w-3 h-3 rounded-full bg-gray-300 border-2 border-white" />
              <div className="text-xs text-[#8e9ab5]">{endDate}</div>
              <div className="text-sm">STEM OPT ends</div>
            </div>
          )}
        </div>
      </div>

      {/* Findings */}
      {issues.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-red-600 uppercase tracking-wider mb-3">
            ⚠️ Needs Attention ({issues.length})
          </h2>
          <div className="flex flex-col gap-2">
            {issues.map((f) => (
              <div key={f.id} className={`rounded-xl px-5 py-4 text-sm ${f.severity === "critical" ? "bg-red-50/60 border border-red-200/30" : "bg-amber-50/60 border border-amber-200/30"}`}>
                <div className="font-semibold text-[#0d1424] mb-1">{f.title}</div>
                <div className="text-[#556480]">{f.action}</div>
                <div className="flex gap-2 mt-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${f.severity === "critical" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                    {f.consequence}
                  </span>
                  {f.immigration_impact && (
                    <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-700">🛂 Immigration impact</span>
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
          <h2 className="text-sm font-semibold text-green-600 uppercase tracking-wider mb-3">
            ✓ Looks Good ({goods.length})
          </h2>
          <div className="bg-green-50/40 rounded-xl px-5 py-3 text-sm text-[#556480]">
            {goods.map((g) => g.field_name.replace(/_/g, " ")).join(" · ")}
          </div>
        </div>
      )}

      {/* Advisories */}
      {advisories.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-[#7b8ba5] uppercase tracking-wider mb-3">
            Also worth checking
          </h2>
          <div className="flex flex-col gap-2">
            {advisories.map((a) => (
              <div key={a.id} className="flex items-start gap-3 py-3 border-b border-blue-50/30 last:border-0">
                <div className="flex-1 text-sm">
                  <span className="font-medium text-[#3d6bc5]">{a.title}</span>
                  <span className="text-[#556480]"> — {a.action}</span>
                </div>
                <span className="text-xs text-red-600 whitespace-nowrap">{a.consequence}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Save CTA */}
      <div className="text-center pt-6 border-t border-blue-100/20">
        <button className="px-8 py-4 rounded-xl bg-[#1a2036] text-white font-semibold text-[15px] shadow-md hover:shadow-lg transition-all">
          Save as my case
        </button>
        <p className="text-xs text-[#8e9ab5] mt-3">Bookmark this URL to return anytime</p>
      </div>
    </div>
  );
}
