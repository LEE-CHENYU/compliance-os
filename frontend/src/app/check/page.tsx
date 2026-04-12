"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

import { trackForm8843FunnelEvent, trackOnboardingEvent } from "@/lib/analytics";
import { inferForm8843CheckPath, readForm8843OnboardingHandoff } from "@/lib/form8843-handoff";

export default function CheckSelect() {
  const router = useRouter();
  const viewedRef = useRef(false);

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

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-2xl">
        <button onClick={() => router.push("/")} className="text-sm text-[#7b8ba5] mb-8 hover:text-[#1a2036]">
          &larr; Back
        </button>

        <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
          What do you want to check?
        </h1>
        <p className="text-[15px] text-[#556480] mb-8">
          Pick the area that matters most right now. You can always run the other check later.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <button
            onClick={() => handleTrackSelect("stem_opt", "/check/stem-opt")}
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
