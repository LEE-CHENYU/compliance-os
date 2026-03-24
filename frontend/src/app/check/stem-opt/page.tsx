"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createCheck } from "@/lib/api-v2";

const STAGES = [
  { value: "stem_opt", label: "On STEM OPT", sub: "24-month extension active" },
  { value: "opt", label: "On post-completion OPT", sub: "Initial 12-month period" },
  { value: "applying_stem", label: "Applying for STEM extension", sub: "" },
  { value: "pre_completion", label: "Pre-completion (CPT)", sub: "" },
  { value: "not_sure", label: "Not sure", sub: "" },
];

export default function StemOptStage() {
  const router = useRouter();
  const [stage, setStage] = useState<string | null>(null);
  const [years, setYears] = useState<number | "">("");
  const [loading, setLoading] = useState(false);

  const canContinue = stage && years !== "";

  async function handleContinue() {
    if (!canContinue) return;
    setLoading(true);
    const check = await createCheck("stem_opt", { stage, years_in_us: Number(years) });
    router.push(`/check/stem-opt/upload?id=${check.id}`);
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-lg">
        <button onClick={() => router.push("/")} className="text-sm text-[#7b8ba5] mb-8 hover:text-[#1a2036]">
          ← Back
        </button>

        <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
          What&apos;s your current stage?
        </h1>
        <p className="text-[15px] text-[#556480] mb-8">
          This helps us know which checks matter for you.
        </p>

        <div className="flex flex-col gap-2.5 mb-8">
          {STAGES.map((s) => (
            <button
              key={s.value}
              onClick={() => setStage(s.value)}
              className={`text-left px-5 py-4 rounded-xl border transition-all ${
                stage === s.value
                  ? "border-[#5b8dee] bg-blue-50/80 shadow-sm"
                  : "border-white/70 bg-white/60 hover:bg-white/80"
              }`}
            >
              <div className="font-semibold text-[15px]">{s.label}</div>
              {s.sub && <div className="text-xs text-[#8e9ab5] mt-0.5">{s.sub}</div>}
            </button>
          ))}
        </div>

        <div className="mb-10">
          <label className="block text-sm font-medium text-[#0d1424] mb-2">
            How many years have you been in the US on F-1?
          </label>
          <input
            type="number"
            min={0}
            max={20}
            value={years}
            onChange={(e) => setYears(e.target.value === "" ? "" : Number(e.target.value))}
            placeholder="e.g., 4"
            className="w-24 px-4 py-3 rounded-xl border border-white/70 bg-white/60 text-[15px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
          />
        </div>

        <button
          onClick={handleContinue}
          disabled={!canContinue || loading}
          className={`w-full py-4 rounded-xl font-semibold text-[15px] transition-all ${
            canContinue
              ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_4px_16px_rgba(74,116,212,0.3)] hover:shadow-[0_8px_28px_rgba(74,116,212,0.4)]"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          {loading ? "Creating..." : "Continue"}
        </button>
      </div>
    </div>
  );
}
