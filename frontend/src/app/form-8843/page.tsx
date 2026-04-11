"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import OnboardingWizard, { type Form8843WizardState } from "@/components/form8843/OnboardingWizard";
import { generateForm8843, type Form8843Request } from "@/lib/marketplace";


const INITIAL_STATE: Form8843WizardState = {
  full_name: "",
  email: "",
  visa_type: "F-1",
  school_name: "",
  school_address: "",
  school_contact: "",
  program_director: "",
  current_nonimmigrant_status: "",
  arrival_date: "",
  country_citizenship: "",
  country_passport: "",
  passport_number: "",
  us_taxpayer_id: "",
  address_country: "",
  address_us: "",
  days_present_current: "",
  days_present_year_1_ago: "0",
  days_present_year_2_ago: "0",
  days_excludable_current: "0",
  changed_status: false,
  applied_for_residency: false,
  filing_with_tax_return: false,
};

export default function Form8843Page() {
  const router = useRouter();
  const [form, setForm] = useState<Form8843WizardState>(INITIAL_STATE);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function setField<K extends keyof Form8843WizardState>(key: K, value: Form8843WizardState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) {
      return;
    }

    setSubmitting(true);
    setError(null);

    const payload: Form8843Request = {
      email: form.email.trim(),
      full_name: form.full_name.trim(),
      visa_type: form.visa_type.trim(),
      school_name: form.school_name.trim(),
      country_citizenship: form.country_citizenship.trim(),
      country_passport: form.country_passport.trim() || undefined,
      passport_number: form.passport_number.trim() || undefined,
      current_nonimmigrant_status: form.current_nonimmigrant_status.trim() || undefined,
      arrival_date: form.arrival_date || undefined,
      school_address: form.school_address.trim() || undefined,
      school_contact: form.school_contact.trim() || undefined,
      program_director: form.program_director.trim() || undefined,
      us_taxpayer_id: form.us_taxpayer_id.trim() || undefined,
      address_country: form.address_country.trim() || undefined,
      address_us: form.address_us.trim() || undefined,
      days_present_current: Number(form.days_present_current || 0),
      days_present_year_1_ago: Number(form.days_present_year_1_ago || 0),
      days_present_year_2_ago: Number(form.days_present_year_2_ago || 0),
      days_excludable_current: Number(form.days_excludable_current || 0),
      changed_status: form.changed_status,
      applied_for_residency: form.applied_for_residency,
      filing_with_tax_return: form.filing_with_tax_return,
    };

    try {
      const response = await generateForm8843(payload);
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(
          "guardian_form_8843_onboarding",
          JSON.stringify({
            orderId: response.order_id,
            email: payload.email,
          }),
        );
      }
      router.push(`/form-8843/success?orderId=${encodeURIComponent(response.order_id)}`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not generate Form 8843");
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(91,141,238,0.18),_transparent_32%),linear-gradient(180deg,#edf3f9_0%,#e6eef6_42%,#f4f7fb_100%)] px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex items-center justify-between">
          <button
            type="button"
            onClick={() => router.push("/")}
            className="rounded-full border border-white/80 bg-white/75 px-4 py-2 text-sm font-medium text-[#52627d] shadow-[0_8px_24px_rgba(42,64,102,0.08)] backdrop-blur hover:text-[#1a2036]"
          >
            ← Back
          </button>
          <div className="rounded-full border border-[#dce6f3] bg-white/80 px-4 py-2 text-[12px] font-semibold uppercase tracking-[0.18em] text-[#6d7c95] shadow-[0_8px_24px_rgba(42,64,102,0.08)]">
            Free filing tool
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.05fr,0.95fr]">
          <section className="rounded-[32px] border border-white/70 bg-white/72 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
            <div className="mb-10 max-w-2xl">
              <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">Free Form 8843</div>
              <h1 className="mt-3 text-[40px] font-extrabold tracking-tight text-[#0d1424]">Generate your Form 8843 and get clear filing instructions</h1>
              <p className="mt-4 max-w-xl text-[16px] leading-7 text-[#556480]">
                Answer a few questions, download the completed PDF, and see exactly how to file it. No account is required to get started.
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Link
                  href="/login?next=/dashboard"
                  className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-5 py-3 text-[14px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
                >
                  Already use Guardian? Sign in
                </Link>
              </div>
            </div>

            <OnboardingWizard
              form={form}
              setField={setField}
              submitting={submitting}
              error={error}
              onSubmit={handleSubmit}
            />
          </section>

          <aside className="rounded-[32px] border border-white/70 bg-[#f8fbff]/78 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
            <div className="rounded-[28px] bg-[#0f1728] p-6 text-white shadow-[0_22px_50px_rgba(9,18,36,0.24)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8ca2cc]">What you get</div>
              <div className="mt-3 text-[26px] font-bold leading-tight">A completed Form 8843, clear filing steps, and an easy way to keep track of it in Guardian.</div>
              <p className="mt-4 text-[14px] leading-7 text-[#c9d5eb]">
                This is built to help you finish the filing, not just download a PDF and figure the rest out yourself.
              </p>
            </div>

            <div className="mt-6 space-y-4">
              {[
                ["1", "Answer only the details needed to prepare the form."],
                ["2", "Download a completed PDF that is ready to print and sign."],
                ["3", "See whether to mail it directly or include it with your tax return package."],
                ["4", "Optionally save it in Guardian so you can track whether you already mailed it."],
              ].map(([step, copy]) => (
                <div key={step} className="flex gap-4 rounded-2xl border border-[#dbe5f2] bg-white/82 p-4 shadow-[0_10px_30px_rgba(61,84,128,0.05)]">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#edf4ff] text-[14px] font-bold text-[#315aa5]">
                    {step}
                  </div>
                  <p className="text-[14px] leading-6 text-[#4c5f7a]">{copy}</p>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-[24px] border border-dashed border-[#c9d7eb] bg-white/70 p-5">
              <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">Important</div>
              <p className="mt-3 text-[14px] leading-6 text-[#5f6f88]">
                Form 8843 by itself cannot be e-filed. The next screen will show the correct filing path and give you the mailing steps if they apply.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
