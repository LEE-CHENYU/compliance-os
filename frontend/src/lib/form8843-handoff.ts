"use client";

export const FORM8843_ONBOARDING_STORAGE_KEY = "guardian_form_8843_onboarding";

export type Form8843OnboardingHandoff = {
  orderId?: string;
  email?: string;
  visa_type?: string;
  current_nonimmigrant_status?: string;
  arrival_date?: string;
  country_citizenship?: string;
  school_name?: string;
  guided_handoff?: boolean;
};

function normalize(value: string | null | undefined): string {
  return (value || "").trim().toUpperCase();
}

export function readForm8843OnboardingHandoff(): Form8843OnboardingHandoff | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.sessionStorage.getItem(FORM8843_ONBOARDING_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as Form8843OnboardingHandoff;
  } catch {
    window.sessionStorage.removeItem(FORM8843_ONBOARDING_STORAGE_KEY);
    return null;
  }
}

export function inferForm8843CheckPath(handoff: Form8843OnboardingHandoff | null): string | null {
  if (!handoff) {
    return null;
  }

  const visa = normalize(handoff.visa_type);
  const status = normalize(handoff.current_nonimmigrant_status);
  const combined = `${visa} ${status}`;

  if (combined.includes("STEM OPT")) {
    return "/check/stem-opt";
  }
  if (combined.includes("OPT")) {
    return "/check/stem-opt";
  }
  if (combined.includes("H-1B") || combined.includes("H1B") || combined.includes("I-140")) {
    return "/check/stem-opt";
  }
  if (
    combined.includes("F-1")
    || combined.includes("J-1")
    || combined.includes("M-1")
    || combined.includes("Q")
    || Boolean(handoff.school_name)
  ) {
    return "/check/student";
  }
  return null;
}

export function buildForm8843CheckHref(handoff: Form8843OnboardingHandoff | null): string {
  const inferredPath = inferForm8843CheckPath(handoff);
  if (!inferredPath) {
    return "/check?source=form8843";
  }
  return `${inferredPath}?source=form8843`;
}

export function deriveYearsInUs(arrivalDate: string | null | undefined): string {
  if (!arrivalDate) {
    return "";
  }
  const parsed = new Date(arrivalDate);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  const years = Math.max(1, new Date().getFullYear() - parsed.getFullYear() + 1);
  return String(years);
}

export function inferStemOptStage(handoff: Form8843OnboardingHandoff | null): string | null {
  if (!handoff) {
    return null;
  }
  const combined = `${normalize(handoff.visa_type)} ${normalize(handoff.current_nonimmigrant_status)}`;
  if (combined.includes("STEM OPT")) {
    return "stem_opt";
  }
  if (combined.includes("OPT")) {
    return "opt";
  }
  if (combined.includes("H-1B") || combined.includes("H1B")) {
    return "h1b";
  }
  if (combined.includes("I-140")) {
    return "i140";
  }
  return null;
}
