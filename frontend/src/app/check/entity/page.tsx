"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createCheck } from "@/lib/api-v2";

const ENTITY_TYPES = [
  { value: "smllc", label: "Single-member LLC" },
  { value: "multi_llc", label: "Multi-member LLC" },
  { value: "c_corp", label: "C-Corporation" },
  { value: "s_corp", label: "S-Corporation" },
  { value: "not_sure", label: "Not sure" },
];

const RESIDENCY_OPTIONS = [
  { value: "us_citizen_or_pr", label: "Yes" },
  { value: "on_visa", label: "No \u2014 on a visa" },
  { value: "outside_us", label: "No \u2014 outside US" },
];

const VISA_TYPES = [
  { value: "f1_opt_stem", label: "F-1 (OPT/STEM)" },
  { value: "h1b", label: "H-1B" },
  { value: "l1", label: "L-1" },
  { value: "o1", label: "O-1" },
  { value: "other", label: "Other" },
];

const YES_NO = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];

const YES_NO_UNSURE = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "not_sure", label: "Not sure" },
];

const FORMATION_AGE = [
  { value: "this_year", label: "This year" },
  { value: "1_2_years", label: "1\u20132 years ago" },
  { value: "3_plus_years", label: "3+ years ago" },
];

type Answers = Record<string, string>;

export default function EntityInfo() {
  const router = useRouter();
  const [answers, setAnswers] = useState<Answers>({});
  const [loading, setLoading] = useState(false);

  const set = (key: string, value: string) => setAnswers((a) => ({ ...a, [key]: value }));

  const showVisa = answers.owner_residency === "on_visa";
  const canContinue =
    answers.entity_type &&
    answers.owner_residency &&
    answers.state_of_formation &&
    answers.separate_bank_account &&
    answers.foreign_capital_transfer &&
    answers.formation_age &&
    (!showVisa || answers.visa_type);

  async function handleContinue() {
    if (!canContinue) return;
    setLoading(true);
    const check = await createCheck("entity", answers);
    router.push(`/check/entity/upload?id=${check.id}`);
  }

  function ChipGroup({ label, options, field }: { label: string; options: { value: string; label: string }[]; field: string }) {
    return (
      <div className="mb-6">
        <div className="text-sm font-medium text-[#0d1424] mb-3">{label}</div>
        <div className="flex flex-wrap gap-2">
          {options.map((o) => (
            <button
              key={o.value}
              onClick={() => set(field, o.value)}
              className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                answers[field] === o.value
                  ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_2px_12px_rgba(74,116,212,0.3)]"
                  : "bg-white/70 backdrop-blur border border-blue-100/30 text-[#3a5a8c] hover:bg-white/90"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-lg py-20">
        <button onClick={() => router.push("/")} className="text-sm text-[#7b8ba5] mb-8 hover:text-[#1a2036]">
          &larr; Back
        </button>

        <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
          Tell us about your entity
        </h1>
        <p className="text-[15px] text-[#556480] mb-8">
          We&apos;ll check if your structure and filings are consistent.
        </p>

        <ChipGroup label="Entity type" options={ENTITY_TYPES} field="entity_type" />
        <ChipGroup label="Are you a US citizen or permanent resident?" options={RESIDENCY_OPTIONS} field="owner_residency" />
        {showVisa && <ChipGroup label="What visa are you on?" options={VISA_TYPES} field="visa_type" />}

        <div className="mb-6">
          <div className="text-sm font-medium text-[#0d1424] mb-3">State of formation</div>
          <input
            type="text"
            value={answers.state_of_formation || ""}
            onChange={(e) => set("state_of_formation", e.target.value)}
            placeholder="e.g., Delaware, Wyoming"
            className="w-full px-4 py-3 rounded-xl border border-white/70 bg-white/60 text-[15px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
          />
        </div>

        <ChipGroup label="Do you have a separate business bank account?" options={YES_NO_UNSURE} field="separate_bank_account" />
        <ChipGroup label="Have you transferred money from a foreign account to fund the business?" options={YES_NO} field="foreign_capital_transfer" />
        <ChipGroup label="When was the entity formed?" options={FORMATION_AGE} field="formation_age" />

        <button
          onClick={handleContinue}
          disabled={!canContinue || loading}
          className={`w-full py-4 rounded-xl font-semibold text-[15px] transition-all mt-4 ${
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
