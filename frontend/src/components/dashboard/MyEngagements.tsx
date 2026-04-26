"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import {
  listCases,
  listMyEngagements,
  type AttentionLabel,
  type Case,
  type EngagementStatus,
  type MyEngagement,
} from "@/lib/api";

/** "My cases" panel for the Guardian dashboard.
 *
 *  Shows ONE row per case the user owns. Cases that have tracked
 *  engagements get the engagement summary nested inside (count + the
 *  most-attention-worthy firm). Cases without engagements still show
 *  a row so the user has a clickable path back to /case/[id] — without
 *  this, a user who created a case (paid + claimed) but hasn't yet
 *  tracked any firms would have no way to find it again from the
 *  dashboard. The whole panel only hides when the user has zero cases.
 */
export default function MyEngagements() {
  const [engagements, setEngagements] = useState<MyEngagement[] | null>(null);
  const [cases, setCases] = useState<Case[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      listMyEngagements().catch((e) => {
        setError(e instanceof Error ? e.message : String(e));
        return [] as MyEngagement[];
      }),
      listCases().catch(() => ({ cases: [] as Case[] })),
    ]).then(([e, c]) => {
      setEngagements(e);
      setCases(c.cases ?? []);
    });
  }, []);

  if (error || engagements === null || cases === null) {
    return null; // Stay quiet — most often this is "not signed in".
  }

  // No cases at all → nothing to show. The whole panel disappears, same
  // as the prior "no engagements" empty state.
  if (cases.length === 0) return null;

  // Group engagements by case for nested rendering. Cases without
  // engagements still get a row (just no nested firms).
  const byCase = new Map<string, MyEngagement[]>();
  for (const e of engagements) {
    const list = byCase.get(e.case_id) ?? [];
    list.push(e);
    byCase.set(e.case_id, list);
  }

  // Sort: cases with activity first (most-recent engagement), then
  // by case created_at desc.
  const sortedCases = [...cases].sort((a, b) => {
    const aLatest = lastActivityForCase(byCase.get(a.id) ?? []);
    const bLatest = lastActivityForCase(byCase.get(b.id) ?? []);
    if (aLatest && bLatest) return bLatest.localeCompare(aLatest);
    if (aLatest) return -1;
    if (bLatest) return 1;
    return b.created_at.localeCompare(a.created_at);
  });

  const totalAttention = engagements.filter((e) => e.attention_label !== null).length;

  return (
    <section className="mb-8 overflow-hidden rounded-[28px] border border-white/60 bg-[linear-gradient(135deg,rgba(255,255,255,0.78),rgba(234,241,251,0.92))] backdrop-blur-xl shadow-[0_10px_36px_rgba(91,141,238,0.08)]">
      <div className="p-5 md:p-7">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
              My cases
            </div>
            <h2 className="mt-2 text-[24px] font-bold leading-tight text-[#0d1424]">
              Track outreach across every case in one place
            </h2>
            <p className="mt-3 text-[14px] leading-7 text-[#556480]">
              Each case shows the firms you&rsquo;re working with and inbound
              replies from Gmail. Click a case to manage engagements, notes,
              and email threads.
            </p>
            {totalAttention > 0 && (
              <p className="mt-2 text-[12px] font-medium text-[#5b8dee]">
                {totalAttention} {totalAttention === 1 ? "firm needs" : "firms need"} your attention
              </p>
            )}
          </div>
        </div>

        <ul className="mt-6 space-y-3">
          {sortedCases.map((c) => {
            const caseEngagements = byCase.get(c.id) ?? [];
            return <CaseRow key={c.id} c={c} engagements={caseEngagements} />;
          })}
        </ul>
      </div>
    </section>
  );
}


function CaseRow({ c, engagements }: { c: Case; engagements: MyEngagement[] }) {
  // Pick the most attention-worthy engagement to feature in the row.
  // Backend already pre-sorted listMyEngagements by attention priority,
  // so the first one wins.
  const featured = engagements[0];
  const attentionCount = engagements.filter((e) => e.attention_label !== null).length;
  const label = c.workflow_type
    ? `${c.workflow_type.charAt(0).toUpperCase()}${c.workflow_type.slice(1)} case`
    : "Case";

  return (
    <li className="rounded-2xl border border-[#e4edf7] bg-white/82 p-4 shadow-[0_10px_30px_rgba(61,84,128,0.05)]">
      <Link
        href={`/case/${c.id}`}
        className="block hover:bg-stone-50/50 -mx-2 -my-1 px-2 py-1 rounded-lg transition-colors"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span className="text-[15px] font-semibold text-[#0d1424] truncate">
                {label}
              </span>
              <span className="text-[11px] font-mono text-[#7b8ba5]">
                {c.id.slice(0, 8)}
              </span>
              {attentionCount > 0 && (
                <span className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-700">
                  {attentionCount} need attention
                </span>
              )}
            </div>
            <div className="mt-1 text-[12px] text-[#7b8ba5]">
              {engagements.length === 0 ? (
                <>
                  No firms tracked yet · created {fmtRel(c.created_at)}
                </>
              ) : (
                <>
                  {engagements.length} {engagements.length === 1 ? "firm" : "firms"} tracked ·
                  last activity {fmtRel(featured?.last_activity_at ?? c.updated_at)}
                </>
              )}
            </div>
            {featured && (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px]">
                <span className="font-medium text-[#40536f]">{featured.firm_name}</span>
                <EngagementStatusPill status={featured.status} />
                {featured.attention_label && (
                  <AttentionBadge label={featured.attention_label} />
                )}
                {engagements.length > 1 && (
                  <span className="text-[11px] text-[#9aa9c2]">
                    +{engagements.length - 1} more
                  </span>
                )}
              </div>
            )}
            {!featured && (
              <div className="mt-2 text-[12px] font-medium text-[#5b8dee]">
                Open case to find lawyers →
              </div>
            )}
          </div>
          <span className="shrink-0 text-[12px] text-[#7b8ba5]">→</span>
        </div>
      </Link>
    </li>
  );
}


function lastActivityForCase(engagements: MyEngagement[]): string | null {
  if (engagements.length === 0) return null;
  return engagements.reduce<string | null>((latest, e) => {
    if (!e.last_activity_at) return latest;
    if (!latest) return e.last_activity_at;
    return e.last_activity_at > latest ? e.last_activity_at : latest;
  }, null);
}


function AttentionBadge({ label }: { label: AttentionLabel }) {
  const config: Record<AttentionLabel, { text: string; cls: string }> = {
    new_reply: {
      text: "← new reply",
      cls: "border-blue-200 bg-blue-50 text-blue-700",
    },
    needs_followup: {
      text: "needs follow-up",
      cls: "border-amber-200 bg-amber-50 text-amber-700",
    },
    awaiting_response: {
      text: "awaiting response",
      cls: "border-stone-200 bg-stone-50 text-stone-500",
    },
  };
  const { text, cls } = config[label];
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}
    >
      {text}
    </span>
  );
}


function EngagementStatusPill({ status }: { status: EngagementStatus }) {
  const map: Record<EngagementStatus, string> = {
    not_contacted: "bg-stone-100 text-stone-600 border-stone-200",
    outreach_sent: "bg-blue-50 text-blue-700 border-blue-200",
    in_discussion: "bg-violet-50 text-violet-700 border-violet-200",
    engaged: "bg-emerald-50 text-emerald-700 border-emerald-200",
    declined: "bg-stone-50 text-stone-400 border-stone-200",
  };
  const label = {
    not_contacted: "not contacted",
    outreach_sent: "outreach sent",
    in_discussion: "in discussion",
    engaged: "engaged",
    declined: "declined",
  }[status];
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${map[status]}`}
    >
      {label}
    </span>
  );
}


function fmtRel(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const ms = Date.now() - d.getTime();
  const min = Math.round(ms / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min} min ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.round(hr / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}
