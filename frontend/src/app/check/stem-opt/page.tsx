"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createCheck } from "@/lib/api-v2";
import { deriveYearsInUs, inferStemOptStage, readForm8843OnboardingHandoff } from "@/lib/form8843-handoff";

const STAGES = [
  { value: "pre_completion", label: "CPT (Pre-completion)", sub: "Curricular Practical Training while enrolled" },
  { value: "opt", label: "Post-completion OPT", sub: "12-month work authorization after graduation" },
  { value: "stem_opt", label: "STEM OPT Extension", sub: "24-month STEM extension" },
  { value: "h1b", label: "H-1B", sub: "Employer-sponsored specialty occupation visa" },
  { value: "i140", label: "I-140 / Green Card Process", sub: "Employment-based immigrant petition in progress" },
  { value: "not_sure", label: "Not sure", sub: "" },
];

const TAX_SOFTWARE = [
  { value: "turbotax", label: "TurboTax" },
  { value: "hr_block", label: "H&R Block" },
  { value: "sprintax", label: "Sprintax" },
  { value: "cpa", label: "A CPA / accountant" },
  { value: "not_filed", label: "Haven\u2019t filed yet" },
  { value: "not_sure", label: "Not sure" },
];

const EMPLOYMENT_STATUS = [
  { value: "employed", label: "Yes, currently employed" },
  { value: "between_jobs", label: "Between jobs" },
  { value: "not_employed", label: "Not currently employed" },
];

const EMPLOYER_CHANGED = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "na", label: "N/A" },
];

const PETITION_STATUS = [
  { value: "approved", label: "Yes, approved" },
  { value: "pending", label: "Pending" },
  { value: "not_sure", label: "Not sure" },
];

export default function StemOptStage() {
  const router = useRouter();
  const [stage, setStage] = useState<string | null>(null);
  const [years, setYears] = useState<number | "">("");
  const [employmentStatus, setEmploymentStatus] = useState<string | null>(null);
  const [employerChanged, setEmployerChanged] = useState<string | null>(null);
  const [petitionStatus, setPetitionStatus] = useState<string | null>(null);
  const [taxSoftware, setTaxSoftware] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [prefillContext, setPrefillContext] = useState<Record<string, string>>({});
  const [form8843PrefillNote, setForm8843PrefillNote] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const source = new URLSearchParams(window.location.search).get("source");
    if (source !== "form8843") {
      return;
    }
    const handoff = readForm8843OnboardingHandoff();
    if (!handoff) {
      return;
    }

    const inferredStage = inferStemOptStage(handoff);
    const inferredYears = deriveYearsInUs(handoff.arrival_date);
    if (inferredStage) {
      setStage((current) => current || inferredStage);
    }
    if (inferredYears) {
      setYears((current) => (current === "" ? Number(inferredYears) : current));
    }
    setPrefillContext({
      source_form_8843: "yes",
      visa_type: handoff.visa_type || "",
      current_nonimmigrant_status: handoff.current_nonimmigrant_status || "",
      arrival_date: handoff.arrival_date || "",
      country_citizenship: handoff.country_citizenship || "",
      school_name: handoff.school_name || "",
    });
    setForm8843PrefillNote("We carried over your visa, arrival date, citizenship, and years in the U.S. from Form 8843.");
  }, []);

  const showEmployerChanged = stage && ["stem_opt", "opt", "h1b", "i140"].includes(stage);
  const showPetitionStatus = stage && ["h1b", "i140"].includes(stage);
  const canContinue = stage && years !== "" && employmentStatus && taxSoftware
    && (!showEmployerChanged || employerChanged)
    && (!showPetitionStatus || petitionStatus);

  async function handleContinue() {
    if (!canContinue) return;
    setLoading(true);
    const check = await createCheck("stem_opt", {
      stage,
      years_in_us: Number(years),
      employment_status: employmentStatus,
      employer_changed: employerChanged,
      petition_status: petitionStatus,
      tax_software_used: taxSoftware,
      ...prefillContext,
    });
    router.push(`/check/stem-opt/upload?id=${check.id}`);
  }

  function ChipSelect({ label, options, value, onChange }: {
    label: string;
    options: { value: string; label: string }[];
    value: string | null;
    onChange: (v: string) => void;
  }) {
    return (
      <div className="mb-8">
        <div className="text-sm font-medium text-[#0d1424] mb-3">{label}</div>
        <div className="flex flex-wrap gap-2">
          {options.map((o) => (
            <button
              key={o.value}
              onClick={() => onChange(o.value)}
              className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                value === o.value
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
        <button onClick={() => router.push("/check")} className="text-sm text-[#7b8ba5] mb-8 hover:text-[#1a2036]">
          &larr; Back
        </button>

        <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
          A few quick questions
        </h1>
        <p className="text-[15px] text-[#556480] mb-8">
          This helps us know which risks to check for.
        </p>

        {form8843PrefillNote ? (
          <div className="mb-8 rounded-2xl border border-[#dbe5f2] bg-[#f8fbff] px-4 py-3 text-[14px] leading-6 text-[#556480]">
            {form8843PrefillNote}
          </div>
        ) : null}

        {/* Q1: Stage */}
        <div className="mb-8">
          <div className="text-sm font-medium text-[#0d1424] mb-3">What&apos;s your current stage?</div>
          <div className="flex flex-col gap-2.5">
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
        </div>

        {/* Q2: Years */}
        <div className="mb-8">
          <label className="block text-sm font-medium text-[#0d1424] mb-3">
            How many years have you been in the US?
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

        {/* Q3: Employment status */}
        <ChipSelect
          label="Are you currently employed?"
          options={EMPLOYMENT_STATUS}
          value={employmentStatus}
          onChange={setEmploymentStatus}
        />

        {/* Q4: Employer changed (conditional) */}
        {showEmployerChanged && (
          <ChipSelect
            label={stage === "h1b" || stage === "i140"
              ? "Have you changed employers since your current petition was filed?"
              : "Have you changed employers since your OPT/STEM started?"}
            options={EMPLOYER_CHANGED}
            value={employerChanged}
            onChange={setEmployerChanged}
          />
        )}

        {/* Q5: Petition status (H-1B and I-140 only) */}
        {showPetitionStatus && (
          <ChipSelect
            label={stage === "i140"
              ? "Has your I-140 petition been approved?"
              : "Has your H-1B petition been approved?"}
            options={PETITION_STATUS}
            value={petitionStatus}
            onChange={setPetitionStatus}
          />
        )}

        {/* Q6: Tax software */}
        <ChipSelect
          label="What did you use to file your most recent US tax return?"
          options={TAX_SOFTWARE}
          value={taxSoftware}
          onChange={setTaxSoftware}
        />

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
