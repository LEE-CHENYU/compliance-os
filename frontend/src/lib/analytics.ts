"use client";

type MixpanelClient = {
  track?: (event: string, properties?: Record<string, unknown>) => void;
};

type Form8843FunnelEvent =
  | "form_8843_gtm_landing_viewed"
  | "form_8843_gtm_step_viewed"
  | "form_8843_gtm_step_completed"
  | "form_8843_gtm_generate_submitted"
  | "form_8843_gtm_generate_succeeded"
  | "form_8843_gtm_generate_failed"
  | "form_8843_gtm_success_viewed"
  | "form_8843_gtm_signin_prompt_viewed"
  | "form_8843_gtm_signin_cta_clicked"
  | "form_8843_gtm_auth_viewed"
  | "form_8843_gtm_auth_submitted"
  | "form_8843_gtm_auth_succeeded"
  | "form_8843_gtm_auth_failed"
  | "form_8843_gtm_download_started"
  | "form_8843_gtm_download_completed"
  | "form_8843_gtm_download_failed"
  | "form_8843_gtm_onboarding_prompt_viewed"
  | "form_8843_gtm_onboarding_cta_clicked"
  | "form_8843_gtm_check_path_inferred"
  | "form_8843_gtm_check_path_ambiguous"
  | "form_8843_gtm_check_intake_viewed"
  | "form_8843_gtm_check_created"
  | "form_8843_gtm_upload_viewed"
  | "form_8843_gtm_document_uploaded"
  | "form_8843_gtm_review_continued";

type MixpanelWindow = Window & {
  mixpanel?: MixpanelClient;
};

function getMixpanel(): MixpanelClient | null {
  if (typeof window === "undefined") {
    return null;
  }
  return ((window as MixpanelWindow).mixpanel ?? null);
}

function safelyInvokeMixpanel(action: () => void) {
  try {
    action();
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      console.warn("Mixpanel call skipped", error);
    }
  }
}

export function trackMixpanelEvent(event: string, properties: Record<string, unknown> = {}) {
  if (process.env.NODE_ENV !== "production") {
    return;
  }

  const mixpanel = getMixpanel();
  if (!mixpanel?.track) {
    return;
  }

  safelyInvokeMixpanel(() => {
    mixpanel.track?.(event, properties);
  });
}

export function trackForm8843FunnelEvent(
  event: Form8843FunnelEvent,
  properties: Record<string, unknown> = {},
) {
  trackMixpanelEvent(event, {
    funnel: "form_8843_gtm",
    source: "form8843",
    ...properties,
  });
}

export function isForm8843GtmNextPath(nextPath: string | null | undefined): boolean {
  if (!nextPath) {
    return false;
  }

  return nextPath.includes("/form-8843/success")
    || nextPath.includes("source=form8843");
}

export function slugifyAnalyticsLabel(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}
