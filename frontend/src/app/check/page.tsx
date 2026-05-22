"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { trackForm8843FunnelEvent, trackOnboardingEvent } from "@/lib/analytics";
import { inferForm8843CheckPath, readForm8843OnboardingHandoff } from "@/lib/form8843-handoff";
import { isLoggedIn, authHeaders } from "@/lib/auth";
import {
  listCases,
  listMySearches,
  listMyEngagements,
} from "@/lib/api";

export default function CheckSelect() {
  const router = useRouter();
  const viewedRef = useRef(false);
  // Block render until we've checked whether the signed-in user already
  // has lawyer content — we don't want them to glimpse the persona
  // picker before being bounced to their actual case/dashboard.
  const [authGateChecked, setAuthGateChecked] = useState(false);

  // If the signed-in user already has ANY meaningful content — searches,
  // engagements, cases, docs, or marketplace activity — /check is the
  // wrong destination. They're not a brand-new account, and the persona
  // picker is just noise. Redirect to /case/{id} when a search/engagement
  // has one (richest landing); otherwise /dashboard.
  //
  // Mirror of the dashboard's anti-bounce gate, intentionally — these
  // two surfaces should be symmetric: if dashboard wouldn't redirect a
  // user to /check, /check shouldn't trap them either.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!isLoggedIn()) {
      setAuthGateChecked(true);
      return;
    }
    let cancelled = false;
    const API = "/api";
    Promise.all([
      listMySearches().catch(() => []),
      listMyEngagements().catch(() => []),
      listCases().catch(() => ({ cases: [] })),
      fetch(`${API}/dashboard/documents`, { headers: authHeaders() })
        .then((r) => (r.ok ? r.json() : []))
        .catch(() => []),
      fetch(`${API}/dashboard/timeline`, { headers: authHeaders() })
        .then((r) => (r.ok ? r.json() : {}))
        .catch(() => ({})),
    ]).then(([searches, engagements, casesResp, docs, tlAny]) => {
      if (cancelled) return;
      const cases = casesResp?.cases ?? [];
      const docList = Array.isArray(docs) ? docs : [];
      type TimelineService = {
        service_summary?: {
          active_orders?: unknown[];
          recent_completed?: unknown[];
          recommended_services?: unknown[];
        };
      };
      const tl = tlAny as TimelineService;
      const hasServiceContent = Boolean(
        tl?.service_summary?.active_orders?.length
          || tl?.service_summary?.recent_completed?.length
          || tl?.service_summary?.recommended_services?.length,
      );
      const hasContent =
        searches.length > 0
        || engagements.length > 0
        || cases.length > 0
        || docList.length > 0
        || hasServiceContent;

      if (hasContent) {
        // Prefer the richest landing: a case attached to a search, then
        // a case attached to an engagement, then any owned case, then
        // the dashboard.
        const searchWithCase = searches.find((s) => s.case_id);
        const engagementWithCase = engagements.find((e) => e.case_id);
        const firstCase = cases[0];
        const caseId =
          searchWithCase?.case_id
          ?? engagementWithCase?.case_id
          ?? firstCase?.id
          ?? null;
        router.replace(caseId ? `/case/${caseId}` : "/dashboard");
        return;
      }
      setAuthGateChecked(true);
    });
    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    if (viewedRef.current) {
      return;
    }
    viewedRef.current = true;
    trackOnboardingEvent("onboarding_track_select_viewed");
  }, []);

  function handleTrackSelect(track: "stem_opt" | "entity" | "student", href: string) {
    trackOnboardingEvent("onboarding_track_selected", {
      check_track: track,
      entry_route: "/check",
    });
    router.push(href);
  }

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const source = new URLSearchParams(window.location.search).get("source");
    if (source !== "form8843") {
      return;
    }
    const nextPath = inferForm8843CheckPath(readForm8843OnboardingHandoff());
    if (nextPath) {
      trackForm8843FunnelEvent("form_8843_gtm_check_path_inferred", {
        onboarding_path: nextPath,
        redirect_mode: "generic_check_router",
      });
      router.replace(`${nextPath}?source=form8843`);
      return;
    }
    trackForm8843FunnelEvent("form_8843_gtm_check_path_ambiguous", {
      redirect_mode: "generic_check_router",
    });
  }, [router]);

  if (!authGateChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center text-[#7b8ba5]">
        Loading…
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-2xl">
        <div className="flex items-center justify-between mb-8">
          <button onClick={() => router.push("/")} className="text-sm text-[#7b8ba5] hover:text-[#1a2036]">
            &larr; Back
          </button>
          <button onClick={() => router.push("/dashboard")} className="text-sm text-[#7b8ba5] hover:text-[#1a2036]">
            Skip &rarr; Dashboard
          </button>
        </div>

        <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
          What do you want to check?
        </h1>
        <p className="text-[15px] text-[#556480] mb-8">
          Pick the area that matters most right now. You can always run the other check later.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <button
            onClick={() => handleTrackSelect("stem_opt", "/check/stem-opt")}
            data-testid="check-track-stem-opt"
            className="text-left bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 p-7 shadow-[0_4px_24px_rgba(91,141,238,0.06)] hover:shadow-[0_8px_32px_rgba(91,141,238,0.1)] hover:-translate-y-1 hover:border-blue-200/30 transition-all"
          >
            <div className="w-11 h-11 rounded-xl bg-blue-50 flex items-center justify-center text-lg font-extrabold text-[#5b8dee] mb-5">A</div>
            <h3 className="text-lg font-bold text-[#0d1424] mb-2">Young Professional</h3>
            <p className="text-[13px] text-[#556480] leading-relaxed mb-4">
              F-1 visa, OPT, STEM OPT, H-1B transition. Check if your immigration documents match your employment records.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {["I-983 cross-check", "Employment match", "Status timeline"].map((t) => (
                <span key={t} className="text-[11px] px-2.5 py-1 rounded-full font-medium backdrop-blur-sm"
                  style={{ background: "rgba(91,141,238,0.08)", color: "#3d6bc5", border: "1px solid rgba(91,141,238,0.1)" }}>
                  {t}
                </span>
              ))}
            </div>
          </button>

          <button
            onClick={() => handleTrackSelect("entity", "/check/entity")}
            data-testid="check-track-entity"
            className="text-left bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 p-7 shadow-[0_4px_24px_rgba(91,141,238,0.06)] hover:shadow-[0_8px_32px_rgba(91,141,238,0.1)] hover:-translate-y-1 hover:border-blue-200/30 transition-all"
          >
            <div className="w-11 h-11 rounded-xl bg-blue-50 flex items-center justify-center text-lg font-extrabold text-[#5b8dee] mb-5">B</div>
            <h3 className="text-lg font-bold text-[#0d1424] mb-2">Entrepreneur</h3>
            <p className="text-[13px] text-[#556480] leading-relaxed mb-4">
              LLC, C-Corp, foreign-owned entity. Check if your business structure and tax filings are consistent.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {["Entity structure", "Tax filing match", "5472 / S-Corp check"].map((t) => (
                <span key={t} className="text-[11px] px-2.5 py-1 rounded-full font-medium backdrop-blur-sm"
                  style={{ background: "rgba(124,58,237,0.08)", color: "#7c3aed", border: "1px solid rgba(124,58,237,0.1)" }}>
                  {t}
                </span>
              ))}
            </div>
          </button>

          <button
            onClick={() => handleTrackSelect("student", "/check/student")}
            data-testid="check-track-student"
            className="text-left bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 p-7 shadow-[0_4px_24px_rgba(91,141,238,0.06)] hover:shadow-[0_8px_32px_rgba(91,141,238,0.1)] hover:-translate-y-1 hover:border-blue-200/30 transition-all"
          >
            <div className="w-11 h-11 rounded-xl bg-blue-50 flex items-center justify-center text-lg font-extrabold text-[#5b8dee] mb-5">C</div>
            <h3 className="text-lg font-bold text-[#0d1424] mb-2">International Student</h3>
            <p className="text-[13px] text-[#556480] leading-relaxed mb-4">
              F-1 student, CPT, travel planning. Check if your I-20 and employment authorization are consistent.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {["CPT authorization", "I-20 vs offer letter", "Travel readiness"].map((t) => (
                <span key={t} className="text-[11px] px-2.5 py-1 rounded-full font-medium backdrop-blur-sm"
                  style={{ background: "rgba(16,185,129,0.08)", color: "#059669", border: "1px solid rgba(16,185,129,0.1)" }}>
                  {t}
                </span>
              ))}
            </div>
          </button>
        </div>

        <p className="text-center text-xs text-[#8e9ab5] mt-6">
          Immigration, tax, and corporate risks are interconnected. We check across all of them.
        </p>
      </div>
    </div>
  );
}
