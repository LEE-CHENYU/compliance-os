"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createCheck } from "@/lib/api-v2";

const STUDENT_STATUS = [
  { value: "enrolled_cpt", label: "Enrolled with CPT", sub: "Currently working on Curricular Practical Training" },
  { value: "enrolled_no_work", label: "Enrolled, not working", sub: "Full-time student, no off-campus employment" },
  { value: "between_semesters", label: "Between semesters", sub: "On break or summer" },
];

const YES_NO = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];

const CPT_MONTHS = [
  { value: "0", label: "None" },
  { value: "1-6", label: "1-6 months" },
  { value: "7-11", label: "7-11 months" },
  { value: "12+", label: "12+ months" },
];

const INCOME_REPORTING = [
  { value: "turbotax", label: "TurboTax" },
  { value: "hr_block", label: "H&R Block" },
  { value: "sprintax", label: "Sprintax" },
  { value: "school_service", label: "My school\u2019s tax service" },
  { value: "cpa", label: "A CPA / accountant" },
  { value: "not_filed", label: "Haven\u2019t filed yet" },
  { value: "no_income", label: "No income to report" },
];

export default function StudentIntake() {
  const router = useRouter();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const set = (key: string, value: string) => setAnswers((a) => ({ ...a, [key]: value }));

  const showCptQuestions = answers.student_status === "enrolled_cpt";
  const showIncomeQuestion = showCptQuestions || answers.student_status === "between_semesters";
  const canContinue = answers.student_status && answers.planning_travel &&
    (!showCptQuestions || (answers.has_cpt_authorization && answers.cpt_fulltime_months)) &&
    (!showIncomeQuestion || answers.income_reporting);

  function ChipSelect({ label, options, field }: { label: string; options: { value: string; label: string; sub?: string }[]; field: string }) {
    return (
      <div className="mb-8">
        <div className="text-sm font-medium text-[#0d1424] mb-3">{label}</div>
        <div className="flex flex-col gap-2">
          {options.map((o) => (
            <button key={o.value} onClick={() => set(field, o.value)}
              className={`text-left px-5 py-3 rounded-xl border transition-all ${
                answers[field] === o.value ? "border-[#5b8dee] bg-blue-50/80 shadow-sm" : "border-white/70 bg-white/60 hover:bg-white/80"
              }`}>
              <div className="font-semibold text-[14px]">{o.label}</div>
              {o.sub && <div className="text-xs text-[#8e9ab5] mt-0.5">{o.sub}</div>}
            </button>
          ))}
        </div>
      </div>
    );
  }

  function ChipRow({ label, options, field }: { label: string; options: { value: string; label: string }[]; field: string }) {
    return (
      <div className="mb-8">
        <div className="text-sm font-medium text-[#0d1424] mb-3">{label}</div>
        <div className="flex flex-wrap gap-2">
          {options.map((o) => (
            <button key={o.value} onClick={() => set(field, o.value)}
              className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                answers[field] === o.value
                  ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_2px_12px_rgba(74,116,212,0.3)]"
                  : "bg-white/70 backdrop-blur border border-blue-100/30 text-[#3a5a8c] hover:bg-white/90"
              }`}>
              {o.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  async function handleContinue() {
    if (!canContinue) return;
    setLoading(true);
    const check = await createCheck("student", {
      ...answers,
      has_employment: answers.student_status === "enrolled_cpt" ? "yes" : "no",
    });
    router.push(`/check/student/upload?id=${check.id}`);
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-lg py-20">
        <button onClick={() => router.push("/check")} className="text-sm text-[#7b8ba5] mb-8 hover:text-[#1a2036]">
          &larr; Back
        </button>

        <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1424] mb-2">
          International Student Check
        </h1>
        <p className="text-[15px] text-[#556480] mb-8">
          We&apos;ll check your I-20, CPT authorization, and travel readiness.
        </p>

        <ChipSelect label="What&apos;s your current situation?" options={STUDENT_STATUS} field="student_status" />

        {showCptQuestions && (
          <>
            <ChipRow label="Is CPT authorization printed on your I-20?" options={YES_NO} field="has_cpt_authorization" />
            <ChipRow label="How many months of full-time CPT have you used total?" options={CPT_MONTHS} field="cpt_fulltime_months" />
          </>
        )}

        {showIncomeQuestion && (
          <ChipRow
            label={showCptQuestions ? "How are you planning to report your CPT income on your taxes?" : "Did you have any US income this year? If so, how are you reporting it?"}
            options={INCOME_REPORTING}
            field="income_reporting"
          />
        )}

        <ChipRow label="Are you planning international travel?" options={YES_NO} field="planning_travel" />

        {answers.planning_travel === "yes" && (
          <ChipRow label="Do you have a pending change of status petition (e.g., H-1B)?" options={[...YES_NO, { value: "not_sure", label: "Not sure" }]} field="pending_status_change" />
        )}

        <button onClick={handleContinue} disabled={!canContinue || loading}
          className={`w-full py-4 rounded-xl font-semibold text-[15px] transition-all mt-4 ${
            canContinue ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-[0_4px_16px_rgba(74,116,212,0.3)]" : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}>
          {loading ? "Creating..." : "Continue"}
        </button>
      </div>
    </div>
  );
}
