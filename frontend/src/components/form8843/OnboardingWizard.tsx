"use client";

import { useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";


export type Form8843WizardState = {
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
  filing_with_tax_return: boolean;
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
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition ${
        checked
          ? "border-[#5b8dee] bg-[#edf4ff] text-[#264781]"
          : "border-[#dbe5f2] bg-white/80 text-[#5f6f88]"
      }`}
    >
      <span>
        <span className="block text-[14px] font-medium">{label}</span>
        {description ? <span className="mt-1 block text-[12px] leading-5 text-[#6f7f99]">{description}</span> : null}
      </span>
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

type StepDefinition = {
  eyebrow: string;
  title: string;
  body: string;
  isValid: (form: Form8843WizardState) => boolean;
};

const STEPS: StepDefinition[] = [
  {
    eyebrow: "Step 1",
    title: "Who should this form be prepared for?",
    body: "Start with the person who will sign and mail the form.",
    isValid: (form) => Boolean(form.full_name.trim() && form.email.trim()),
  },
  {
    eyebrow: "Step 2",
    title: "What visa are you filing under?",
    body: "Form 8843 is most common for F-1, J-1, M-1, and Q visitors.",
    isValid: (form) => Boolean(form.visa_type.trim() && form.arrival_date.trim()),
  },
  {
    eyebrow: "Step 3",
    title: "Which school or program should appear on the form?",
    body: "These details appear on the school and program lines of the IRS form.",
    isValid: (form) => Boolean(form.school_name.trim()),
  },
  {
    eyebrow: "Step 4",
    title: "How should your identity fields be filled?",
    body: "Citizenship is required. Passport details help complete the form cleanly.",
    isValid: (form) => Boolean(form.country_citizenship.trim()),
  },
  {
    eyebrow: "Step 5",
    title: "How many days were you present in the U.S.?",
    body: "These counts help complete the substantial presence section.",
    isValid: (form) => (
      form.days_present_current.trim() !== ""
      && form.days_present_year_1_ago.trim() !== ""
      && form.days_present_year_2_ago.trim() !== ""
    ),
  },
  {
    eyebrow: "Step 6",
    title: "How will you actually file this?",
    body: "This determines whether Guardian shows standalone mailing instructions or tells you to include the form with a tax return package.",
    isValid: () => true,
  },
];

export default function OnboardingWizard({
  form,
  setField,
  submitting,
  error,
  onSubmit,
}: {
  form: Form8843WizardState;
  setField: <K extends keyof Form8843WizardState>(key: K, value: Form8843WizardState[K]) => void;
  submitting: boolean;
  error: string | null;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void> | void;
}) {
  const [stepIndex, setStepIndex] = useState(0);
  const submitIntentRef = useRef(false);
  const step = STEPS[stepIndex];
  const stepComplete = step.isValid(form);
  const isLastStep = stepIndex === STEPS.length - 1;
  const canSubmit = useMemo(
    () => STEPS.every((currentStep) => currentStep.isValid(form)),
    [form],
  );

  function advanceStep() {
    submitIntentRef.current = false;
    setStepIndex((current) => Math.min(STEPS.length - 1, current + 1));
  }

  function handleWizardSubmit(event: FormEvent<HTMLFormElement>) {
    if (!isLastStep) {
      event.preventDefault();
      if (stepComplete) {
        advanceStep();
      }
      return;
    }
    if (!canSubmit || submitting) {
      event.preventDefault();
      return;
    }
    if (!submitIntentRef.current) {
      event.preventDefault();
      return;
    }
    submitIntentRef.current = false;
    void onSubmit(event);
  }

  function handleWizardKeyDown(event: KeyboardEvent<HTMLFormElement>) {
    if (event.key !== "Enter") {
      return;
    }
    if (event.target instanceof HTMLButtonElement) {
      return;
    }
    event.preventDefault();
    if (!isLastStep) {
      if (stepComplete) {
        advanceStep();
      }
    }
  }

  return (
    <form onSubmit={handleWizardSubmit} onKeyDown={handleWizardKeyDown} className="space-y-8">
      <div className="flex items-center gap-2">
        {STEPS.map((currentStep, index) => (
          <button
            key={currentStep.title}
            type="button"
            onClick={() => {
              if (index <= stepIndex || STEPS.slice(0, index).every((item) => item.isValid(form))) {
                setStepIndex(index);
              }
            }}
            className={`h-2.5 flex-1 rounded-full transition ${
              index < stepIndex ? "bg-[#5b8dee]" : index === stepIndex ? "bg-[#8cb0ef]" : "bg-[#dbe5f2]"
            }`}
            aria-label={`Go to ${currentStep.title}`}
          />
        ))}
      </div>

      <div className="rounded-[28px] border border-[#e4edf7] bg-[#fbfdff]/90 p-6 shadow-[0_18px_48px_rgba(61,84,128,0.05)]">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">{step.eyebrow}</div>
        <h2 className="mt-3 text-[28px] font-bold tracking-tight text-[#0d1424]">{step.title}</h2>
        <p className="mt-3 max-w-2xl text-[15px] leading-7 text-[#556480]">{step.body}</p>

        <div className="mt-6">
          {stepIndex === 0 ? (
            <div className="grid gap-5 md:grid-cols-2">
              <Field label="Full name" value={form.full_name} onChange={(value) => setField("full_name", value)} placeholder="Jessica Chen" required />
              <Field label="Email" type="email" value={form.email} onChange={(value) => setField("email", value)} placeholder="jessica@example.com" required />
            </div>
          ) : null}

          {stepIndex === 1 ? (
            <div className="grid gap-5 md:grid-cols-2">
              <Field label="Visa type" value={form.visa_type} onChange={(value) => setField("visa_type", value)} placeholder="F-1" required />
              <Field label="Arrival date" type="date" value={form.arrival_date} onChange={(value) => setField("arrival_date", value)} required />
              <div className="md:col-span-2">
                <Field
                  label="Current status"
                  value={form.current_nonimmigrant_status}
                  onChange={(value) => setField("current_nonimmigrant_status", value)}
                  placeholder="F-1 student"
                />
              </div>
            </div>
          ) : null}

          {stepIndex === 2 ? (
            <div className="grid gap-5 md:grid-cols-2">
              <Field label="School name" value={form.school_name} onChange={(value) => setField("school_name", value)} placeholder="Columbia University" required />
              <Field label="School address" value={form.school_address} onChange={(value) => setField("school_address", value)} placeholder="New York, NY 10027" />
              <Field label="School contact" value={form.school_contact} onChange={(value) => setField("school_contact", value)} placeholder="Office phone or email" />
              <Field label="Program director" value={form.program_director} onChange={(value) => setField("program_director", value)} placeholder="Optional" />
            </div>
          ) : null}

          {stepIndex === 3 ? (
            <div className="grid gap-5 md:grid-cols-2">
              <Field label="Citizenship country" value={form.country_citizenship} onChange={(value) => setField("country_citizenship", value)} placeholder="China" required />
              <Field label="Passport country" value={form.country_passport} onChange={(value) => setField("country_passport", value)} placeholder="Usually the same as citizenship" />
              <Field label="Passport number" value={form.passport_number} onChange={(value) => setField("passport_number", value)} placeholder="E12345678" />
              <Field label="US taxpayer ID" value={form.us_taxpayer_id} onChange={(value) => setField("us_taxpayer_id", value)} placeholder="Optional" />
            </div>
          ) : null}

          {stepIndex === 4 ? (
            <div className="grid gap-5 md:grid-cols-4">
              <Field label="2025" type="number" value={form.days_present_current} onChange={(value) => setField("days_present_current", value)} placeholder="340" required />
              <Field label="2024" type="number" value={form.days_present_year_1_ago} onChange={(value) => setField("days_present_year_1_ago", value)} placeholder="280" required />
              <Field label="2023" type="number" value={form.days_present_year_2_ago} onChange={(value) => setField("days_present_year_2_ago", value)} placeholder="0" required />
              <Field
                label="Excludable days"
                type="number"
                value={form.days_excludable_current}
                onChange={(value) => setField("days_excludable_current", value)}
                placeholder="Usually the same as 2025 days if you were exempt all year"
              />
            </div>
          ) : null}

          {stepIndex === 5 ? (
            <div className="space-y-5">
              <Toggle
                label="I am also filing a Form 1040-NR package"
                description="Turn this on if Form 8843 should travel with a tax return package instead of being mailed by itself."
                checked={form.filing_with_tax_return}
                onChange={(value) => setField("filing_with_tax_return", value)}
              />
              <div className="grid gap-5 md:grid-cols-2">
                <Field label="Home-country address" value={form.address_country} onChange={(value) => setField("address_country", value)} placeholder="Optional" />
                <Field label="US address" value={form.address_us} onChange={(value) => setField("address_us", value)} placeholder="Optional" />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <Toggle
                  label="My nonimmigrant status changed after entry"
                  checked={form.changed_status}
                  onChange={(value) => setField("changed_status", value)}
                />
                <Toggle
                  label="I applied for permanent residency"
                  checked={form.applied_for_residency}
                  onChange={(value) => setField("applied_for_residency", value)}
                />
              </div>

              <details className="rounded-2xl border border-[#dbe5f2] bg-white/80 p-4">
                <summary className="cursor-pointer text-[13px] font-semibold uppercase tracking-[0.16em] text-[#6d7c95]">
                  Optional review details
                </summary>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <Field label="Passport country override" value={form.country_passport} onChange={(value) => setField("country_passport", value)} placeholder="Optional" />
                  <Field label="Program director" value={form.program_director} onChange={(value) => setField("program_director", value)} placeholder="Optional" />
                </div>
              </details>
            </div>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-[#ffd6d6] bg-[#fff4f4] px-4 py-3 text-[14px] text-[#a33a3a]">
          {error}
        </div>
      ) : null}

        <div className="flex flex-col gap-4 border-t border-[#ebf0f7] pt-6 md:flex-row md:items-center md:justify-between">
        <div className="text-[13px] leading-6 text-[#70819c]">
          Your PDF will be generated right away. The next screen will show the filing instructions for your situation.
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          {stepIndex > 0 ? (
            <button
              type="button"
              onClick={() => setStepIndex((current) => Math.max(0, current - 1))}
              className="rounded-full border border-[#dbe5f2] bg-white px-5 py-3 text-[14px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
            >
              Back
            </button>
          ) : null}

          {!isLastStep ? (
            <button
              type="button"
              disabled={!stepComplete}
              onClick={advanceStep}
              className={`rounded-full px-6 py-3 text-[14px] font-semibold transition ${
                stepComplete
                  ? "bg-[#5b8dee] text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] hover:bg-[#4f82de]"
                  : "bg-[#d9e3f0] text-[#90a0bb]"
              }`}
            >
              Continue
            </button>
          ) : (
            <button
              type="submit"
              onClick={() => {
                submitIntentRef.current = true;
              }}
              disabled={!canSubmit || submitting}
              className={`rounded-full px-6 py-3 text-[14px] font-semibold transition ${
                canSubmit && !submitting
                  ? "bg-[#5b8dee] text-white shadow-[0_14px_30px_rgba(91,141,238,0.28)] hover:bg-[#4f82de]"
                  : "bg-[#d9e3f0] text-[#90a0bb]"
              }`}
            >
              {submitting ? "Generating Form 8843..." : "Generate Form 8843"}
            </button>
          )}
        </div>
      </div>
    </form>
  );
}
