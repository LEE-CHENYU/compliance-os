"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { listMySearches, type ProfessionalSearch } from "@/lib/api";

/** "My professional searches" panel for the Guardian dashboard.
 *
 *  Frames the value as the user requested: access reports later,
 *  manage docs, track ongoing communications. Renders quietly when
 *  there are no claimed searches yet (just the value-prop card with
 *  a CTA to start one).
 */
export default function MySearches() {
  const [rows, setRows] = useState<ProfessionalSearch[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMySearches()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error) {
    // Don't render an error pill on the dashboard — most likely cause
    // is the user isn't logged in (different code path) or the endpoint
    // hasn't deployed yet. Stay quiet.
    return null;
  }

  return (
    <section className="mb-8 overflow-hidden rounded-[28px] border border-white/60 bg-[linear-gradient(135deg,rgba(255,255,255,0.78),rgba(234,241,251,0.92))] backdrop-blur-xl shadow-[0_10px_36px_rgba(91,141,238,0.08)]">
      <div className="p-5 md:p-7">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">
              My professional searches
            </div>
            <h2 className="mt-2 text-[24px] font-bold leading-tight text-[#0d1424]">
              Access your reports, manage your docs, and keep track of ongoing
              communications
            </h2>
            <p className="mt-3 text-[14px] leading-7 text-[#556480]">
              Re-download any lawyer search you&rsquo;ve purchased, organize
              the case files those firms need, and capture your back-and-forth
              with each one in a single timeline.
            </p>
          </div>
          <Link
            href="/find-lawyer"
            className="inline-flex shrink-0 items-center gap-2 rounded-full bg-[#5b8dee] px-5 py-2.5 text-[13px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] transition hover:bg-[#4f82de]"
          >
            Start a new search →
          </Link>
        </div>

        {rows === null ? (
          <div className="mt-6 text-[13px] text-[#7b8ba5]">Loading…</div>
        ) : rows.length === 0 ? (
          <div className="mt-6 rounded-2xl border border-dashed border-[#c9d7eb] bg-white/70 p-5 text-[13px] text-[#556480]">
            You haven&rsquo;t purchased a lawyer search yet. Once you do, your
            reports show up here permanently — no expiring links.
          </div>
        ) : (
          <ul className="mt-6 space-y-3">
            {rows.map((r) => (
              <li
                key={r.id}
                className="rounded-2xl border border-[#e4edf7] bg-white/82 p-4 shadow-[0_10px_30px_rgba(61,84,128,0.05)]"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[15px] font-semibold text-[#0d1424]">
                      {r.purpose}
                    </div>
                    <div className="mt-1 text-[12px] text-[#7b8ba5]">
                      {r.vertical.replace(/_/g, " ")} ·{" "}
                      {new Date(r.created_at).toLocaleDateString()}
                      {r.is_paid && r.paid_at && (
                        <>
                          {" "}
                          · <span className="text-[#2f7a45]">paid</span>{" "}
                          {new Date(r.paid_at).toLocaleDateString()}
                        </>
                      )}
                    </div>
                  </div>
                  <Link
                    href={
                      r.is_paid
                        ? `/find-lawyer/${r.id}/paid`
                        : `/find-lawyer/${r.id}`
                    }
                    className="rounded-full border border-[#dbe5f2] bg-white/90 px-4 py-1.5 text-[12px] font-semibold text-[#40536f] transition hover:border-[#5b8dee] hover:text-[#1a2036]"
                  >
                    Open report →
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
