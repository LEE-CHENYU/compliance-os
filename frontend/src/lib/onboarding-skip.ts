export const ONBOARDING_SKIP_DASHBOARD_HREF = "/dashboard?skip_onboarding=1";

const ONBOARDING_SKIP_STORAGE_KEY = "guardian-onboarding-skipped";

export function markOnboardingSkipped() {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(ONBOARDING_SKIP_STORAGE_KEY, "1");
  } catch {
    // The query flag still carries the user through if storage is unavailable.
  }
}

export function shouldBypassOnboardingRedirect(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  const params = new URLSearchParams(window.location.search);
  if (params.get("skip_onboarding") === "1") {
    return true;
  }
  try {
    return window.localStorage.getItem(ONBOARDING_SKIP_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}
