"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { generateForm8843, type Form8843Request } from "@/lib/marketplace";

type FormState = {
  full_name: string;
  email: string;
  visa_type: string;
  school_name: string;
  school_address: string;
  school_contact: string;
  program_director: string;
  current_nonimmigrant_status: string;
  arrival_date: string;
  country_citizenship: string;
  country_passport: string;
  passport_number: string;
  us_taxpayer_id: string;
  address_country: string;
  address_us: string;
  days_present_current: string;
  days_present_year_1_ago: string;
  days_present_year_2_ago: string;
  days_excludable_current: string;
  changed_status: boolean;
  applied_for_residency: boolean;
};

const INITIAL_STATE: FormState = {
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
  days_present_year_1_ago: "",
  days_present_year_2_ago: "",
  days_excludable_current: "0",
  changed_status: false,
  applied_for_residency: false,
};

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="block">
      <div className="mb-2 text-[12px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">
        {label}
        {required ? " *" : ""}
      </div>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-2xl border border-[#dbe5f2] bg-white/90 px-4 py-3 text-[15px] text-[#0d1424] shadow-[0_8px_28px_rgba(61,84,128,0.06)] outline-none transition focus:border-[#5b8dee] focus:ring-4 focus:ring-[#5b8dee]/10"
      />
    </label>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`flex items-center justify-between rounded-2xl border px-4 py-3 text-left transition ${
        checked
          ? "border-[#5b8dee] bg-[#edf4ff] text-[#264781]"
          : "border-[#dbe5f2] bg-white/80 text-[#5f6f88]"
      }`}
    >
      <span className="text-[14px] font-medium">{label}</span>
      <span
        className={`inline-flex h-6 w-11 items-center rounded-full px-1 transition ${
          checked ? "bg-[#5b8dee]" : "bg-[#d7e1ef]"
        }`}
      >
        <span
          className={`h-4 w-4 rounded-full bg-white shadow-sm transition ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </span>
    </button>
  );
}

export default function Form8843Page() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => Boolean(
    form.full_name.trim()
    && form.email.trim()
    && form.visa_type.trim()
    && form.school_name.trim()
    && form.country_citizenship.trim()
    && form.days_present_current.trim()
  ), [form]);

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || submitting) {
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
    };

    try {
      const response = await generateForm8843(payload);
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
            Free IRS workflow
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.05fr,0.95fr]">
          <section className="rounded-[32px] border border-white/70 bg-white/72 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
            <div className="mb-10 max-w-2xl">
              <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">Public Form 8843</div>
              <h1 className="mt-3 text-[40px] font-extrabold tracking-tight text-[#0d1424]">Generate your 2025 Form 8843 in one pass</h1>
              <p className="mt-4 max-w-xl text-[16px] leading-7 text-[#556480]">
                This is the first marketplace slice: a fast public intake that creates the IRS PDF, stores the order, and prepares the follow-up email flow.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-8">
              <div className="grid gap-5 md:grid-cols-2">
                <Field label="Full name" value={form.full_name} onChange={(value) => setField("full_name", value)} placeholder="Jessica Chen" required />
                <Field label="Email" type="email" value={form.email} onChange={(value) => setField("email", value)} placeholder="jessica@example.com" required />
                <Field label="Visa type" value={form.visa_type} onChange={(value) => setField("visa_type", value)} placeholder="F-1" required />
                <Field label="Current status" value={form.current_nonimmigrant_status} onChange={(value) => setField("current_nonimmigrant_status", value)} placeholder="F-1 student" />
                <Field label="School name" value={form.school_name} onChange={(value) => setField("school_name", value)} placeholder="Columbia University" required />
                <Field label="Arrival date" type="date" value={form.arrival_date} onChange={(value) => setField("arrival_date", value)} />
                <Field label="Citizenship country" value={form.country_citizenship} onChange={(value) => setField("country_citizenship", value)} placeholder="China" required />
                <Field label="Passport country" value={form.country_passport} onChange={(value) => setField("country_passport", value)} placeholder="China" />
                <Field label="Passport number" value={form.passport_number} onChange={(value) => setField("passport_number", value)} placeholder="E12345678" />
                <Field label="US taxpayer ID" value={form.us_taxpayer_id} onChange={(value) => setField("us_taxpayer_id", value)} placeholder="Optional" />
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <Field label="School address" value={form.school_address} onChange={(value) => setField("school_address", value)} placeholder="New York, NY 10027" />
                <Field label="School contact" value={form.school_contact} onChange={(value) => setField("school_contact", value)} placeholder="Phone or office" />
                <Field label="Program director" value={form.program_director} onChange={(value) => setField("program_director", value)} placeholder="Optional" />
                <Field label="Home-country address" value={form.address_country} onChange={(value) => setField("address_country", value)} placeholder="Optional" />
                <div className="md:col-span-2">
                  <Field label="US address" value={form.address_us} onChange={(value) => setField("address_us", value)} placeholder="Optional" />
                </div>
              </div>

              <div>
                <div className="mb-4 text-[12px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">Days in the United States</div>
                <div className="grid gap-5 md:grid-cols-4">
                  <Field label="2025" type="number" value={form.days_present_current} onChange={(value) => setField("days_present_current", value)} placeholder="340" required />
                  <Field label="2024" type="number" value={form.days_present_year_1_ago} onChange={(value) => setField("days_present_year_1_ago", value)} placeholder="280" />
                  <Field label="2023" type="number" value={form.days_present_year_2_ago} onChange={(value) => setField("days_present_year_2_ago", value)} placeholder="0" />
                  <Field label="Excludable days" type="number" value={form.days_excludable_current} onChange={(value) => setField("days_excludable_current", value)} placeholder="0" />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <Toggle label="My nonimmigrant status changed after entry" checked={form.changed_status} onChange={(value) => setField("changed_status", value)} />
                <Toggle label="I applied for permanent residency" checked={form.applied_for_residency} onChange={(value) => setField("applied_for_residency", value)} />
              </div>

              {error && (
                <div className="rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
                  {error}
                </div>
              )}

              <div className="flex flex-col gap-3 border-t border-[#ebf0f7] pt-6 md:flex-row md:items-center md:justify-between">
                <p className="max-w-xl text-[13px] leading-6 text-[#70819c]">
                  You can start with the minimum fields and refine later. The backend already stores this as a marketplace order and can attach the email sequence when delivery is configured.
                </p>
                <button
                  type="submit"
                  disabled={!canSubmit || submitting}
                  className={`rounded-full px-6 py-3 text-[15px] font-semibold transition ${
                    canSubmit && !submitting
                      ? "bg-[#5b8dee] text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] hover:bg-[#4f82de]"
                      : "bg-[#d9e3f0] text-[#90a0bb]"
                  }`}
                >
                  {submitting ? "Generating Form 8843..." : "Generate Form 8843"}
                </button>
              </div>
            </form>
          </section>

          <aside className="rounded-[32px] border border-white/70 bg-[#f8fbff]/78 p-8 shadow-[0_24px_70px_rgba(56,85,131,0.08)] backdrop-blur">
            <div className="rounded-[28px] bg-[#0f1728] p-6 text-white shadow-[0_22px_50px_rgba(9,18,36,0.24)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8ca2cc]">What ships in this slice</div>
              <div className="mt-3 text-[26px] font-bold leading-tight">Public intake, PDF generation, order tracking, email boundary.</div>
              <p className="mt-4 text-[14px] leading-7 text-[#c9d5eb]">
                This route is intentionally narrow. It proves the marketplace path with a real service, instead of building generic scaffolding first.
              </p>
            </div>

            <div className="mt-6 space-y-4">
              {[
                ["1", "Collect the minimum facts needed for an initial Form 8843."],
                ["2", "Create a marketplace user and zero-dollar order in the new tables."],
                ["3", "Generate the PDF against the IRS template and expose a download link."],
                ["4", "Queue the welcome sequence once email delivery is configured."],
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
              <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">Current limits</div>
              <p className="mt-3 text-[14px] leading-6 text-[#5f6f88]">
                The generator currently targets the public student workflow first. More nuanced exemption logic and attorney-reviewed execution stay in later slices.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
