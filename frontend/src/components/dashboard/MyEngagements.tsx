"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import {
  listMyEngagements,
  type AttentionLabel,
  type EngagementStatus,
  type MyEngagement,
} from "@/lib/api";

/** "My lawyer engagements" panel for the Guardian dashboard.
 *
 *  Sibling to MySearches. Renders a flat cross-case list of every firm
 *  the user is tracking, sorted by most recent activity. Each row
 *  surfaces the latest email thread direction so users can see at a
 *  glance "did anyone reply since I last looked?".
 */
export default function MyEngagements() {
  const [rows, setRows] = useState<MyEngagement[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMyEngagements()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error || rows === null) {
    return null;  // Stay quiet — most often this is "not signed in".
  }

  // Don't render the section header at all if there are no engagements
  // to show. Keeps the dashboard tidy for users who haven't started
  // tracking yet (who'll see MySearches' empty state instead).
  if (rows.length === 0) return null;

  // Backend pre-sorted by attention priority, but a small "needs your
  // attention" header above the actionable rows lets users know why
  // the order isn't strictly chronological.
  const attentionCount = rows.filter((r) => r.attention_label !== null).length;

  return (
    <section className="mb-8 overflow-hidden rounded-[28px] border border-white/60 bg-[linear-gradient(135deg,rgba(255,255,255,0.78),rgba(234,241,251,0.92))] backdrop-blur-xl shadow-[0_10px_36px_rgba(91,141,238,0.08)]">
      <div className="p-5 md:p-7">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
              My lawyer engagements
            </div>
            <h2 className="mt-2 text-[24px] font-bold leading-tight text-[#0d1424]">
              Track outreach across every case in one place
            </h2>
            <p className="mt-3 text-[14px] leading-7 text-[#556480]">
              Every firm you&rsquo;re working with, sorted by what needs
              attention first. Inbound replies bump the funnel automatically
              when Gmail is connected.
            </p>
            {attentionCount > 0 && (
              <p className="mt-2 text-[12px] font-medium text-[#5b8dee]">
                {attentionCount} {attentionCount === 1 ? "firm needs" : "firms need"} your attention
              </p>
            )}
          </div>
        </div>

        <ul className="mt-6 space-y-2">
          {rows.map((r) => (
            <li
              key={r.id}
              className="rounded-2xl border border-[#e4edf7] bg-white/82 p-4 shadow-[0_10px_30px_rgba(61,84,128,0.05)]"
            >
              <Link
                href={`/case/${r.case_id}`}
                className="block hover:bg-stone-50/50 -mx-2 -my-1 px-2 py-1 rounded-lg transition-colors"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                      <span className="text-[15px] font-semibold text-[#0d1424] truncate">
                        {r.firm_name}
                      </span>
                      <EngagementStatusPill status={r.status} />
                      {r.attention_label && (
                        <AttentionBadge label={r.attention_label} />
                      )}
                    </div>
                    <div className="mt-1 text-[12px] text-[#7b8ba5]">
                      {r.case_workflow_type
                        ? `${r.case_workflow_type} case`
                        : "Case"}
                      {" · "}
                      {r.thread_count > 0
                        ? `${r.thread_count} email thread${r.thread_count === 1 ? "" : "s"}`
                        : "no email threads yet"}
                      {" · "}
                      last activity {fmtRel(r.last_activity_at)}
                    </div>
                    {r.last_thread_subject && (
                      <div className="mt-1 text-[12px] text-[#556480] line-clamp-1">
                        ↳ <em>{r.last_thread_subject}</em>
                      </div>
                    )}
                  </div>
                  <span className="shrink-0 text-[12px] text-[#7b8ba5]">→</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}


function AttentionBadge({ label }: { label: AttentionLabel }) {
  // Color-code by urgency: blue = new info, amber = stale, gray = neutral.
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
