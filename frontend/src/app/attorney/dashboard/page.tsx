"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getUser, isLoggedIn } from "@/lib/auth";
import { getAttorneyDashboard, type AttorneyDashboardResponse } from "@/lib/marketplace";


export const dynamic = "force-dynamic";

function formatDate(value: string | null): string {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function AttorneyDashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<AttorneyDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace(`/login?next=${encodeURIComponent("/attorney/dashboard")}`);
      return;
    }
    if (getUser()?.role !== "attorney") {
      setError("Attorney access is required for this page.");
      setLoading(false);
      return;
    }

    let cancelled = false;
    getAttorneyDashboard()
      .then((nextData) => {
        if (!cancelled) {
          setData(nextData);
        }
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load attorney dashboard");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f5f8fd_0%,#eef4fb_100%)] px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-[#70819e]">Attorney portal</div>
        <h1 className="mt-3 text-[38px] font-bold tracking-tight text-[#0d1424]">Assigned cases</h1>
        <p className="mt-3 max-w-2xl text-[15px] leading-7 text-[#556480]">
          Review straightforward execution-mode cases here, record your checklist decision, and confirm filing once USCIS submission is complete.
        </p>

        {error ? (
          <div className="mt-8 rounded-3xl border border-[#ffd6d6] bg-[#fff4f4] px-5 py-4 text-[14px] text-[#a33a3a]">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="mt-8 rounded-[32px] border border-[#dbe5f2] bg-white/82 px-6 py-8 text-[15px] text-[#6e7f9a] shadow-[0_22px_70px_rgba(61,84,128,0.08)]">
            Loading dashboard...
          </div>
        ) : null}

        {data ? (
          <>
            <section className="mt-8 grid gap-4 md:grid-cols-3">
              <div className="rounded-[28px] border border-[#dbe5f2] bg-white/88 p-6 shadow-[0_18px_60px_rgba(61,84,128,0.08)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Pending review</div>
                <div className="mt-2 text-[28px] font-bold text-[#12213a]">{data.stats.pending_review}</div>
              </div>
              <div className="rounded-[28px] border border-[#dbe5f2] bg-white/88 p-6 shadow-[0_18px_60px_rgba(61,84,128,0.08)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Completed reviews</div>
                <div className="mt-2 text-[28px] font-bold text-[#12213a]">{data.stats.completed_reviews}</div>
              </div>
              <div className="rounded-[28px] border border-[#dbe5f2] bg-white/88 p-6 shadow-[0_18px_60px_rgba(61,84,128,0.08)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Total cases</div>
                <div className="mt-2 text-[28px] font-bold text-[#12213a]">{data.stats.total_cases}</div>
              </div>
            </section>

            <section className="mt-8 rounded-[32px] border border-[#dbe5f2] bg-white/88 p-6 shadow-[0_18px_60px_rgba(61,84,128,0.08)]">
              <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Pending cases</div>
              <div className="mt-4 grid gap-4">
                {data.pending_cases.length ? data.pending_cases.map((item) => (
                  <article key={item.order_id} className="rounded-[24px] border border-[#e4edf7] bg-[#fbfdff] p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">{item.product_sku}</div>
                        <h2 className="mt-2 text-[22px] font-bold tracking-tight text-[#0d1424]">
                          {item.client_name || item.client_email || "Unknown client"}
                        </h2>
                        <p className="mt-2 text-[14px] leading-6 text-[#556480]">
                          Assigned {formatDate(item.assigned_at)} · current status {item.status?.replace(/_/g, " ")}
                        </p>
                      </div>
                      <Link
                        href={`/attorney/cases/${item.order_id}`}
                        className="inline-flex rounded-full bg-[#0f1728] px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-[#18243a]"
                      >
                        Open case
                      </Link>
                    </div>
                  </article>
                )) : (
                  <div className="rounded-[24px] border border-dashed border-[#c8d6ea] bg-[#fbfdff] px-5 py-8 text-[14px] text-[#556480]">
                    No pending cases right now.
                  </div>
                )}
              </div>
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}
