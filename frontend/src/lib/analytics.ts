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

type OnboardingEvent =
  | "onboarding_track_select_viewed"
  | "onboarding_track_selected"
  | "onboarding_intake_viewed"
  | "onboarding_check_created"
  | "onboarding_upload_viewed"
  | "onboarding_document_uploaded"
  | "onboarding_review_phase_viewed"
  | "onboarding_followup_answered"
  | "onboarding_results_viewed"
  | "onboarding_save_clicked";

type SubscriptionEvent =
  | "subscription_pricing_viewed"
  | "subscription_pro_checkout_clicked"
  | "subscription_pro_checkout_failed"
  | "subscription_billing_portal_opened"
  | "subscription_billing_portal_failed"
  | "subscription_paywall_modal_viewed"
  | "subscription_paywall_modal_dismissed"
  | "subscription_paywall_upgrade_clicked"
  | "subscription_quota_badge_clicked"
  | "subscription_pro_free_search_consumed";

type ProfessionalSearchEvent =
  // intake
  | "professional_search_intake_viewed"
  | "professional_search_brief_quality_changed"
  | "professional_search_submitted"
  | "professional_search_submission_failed"
  // status / paywall
  | "professional_search_status_viewed"
  | "professional_search_completed_viewed"
  | "professional_search_paywall_viewed"
  | "professional_search_checkout_clicked"
  | "professional_search_checkout_failed"
  // payment
  | "professional_search_payment_succeeded"
  | "professional_search_payment_polling_timed_out"
  // download
  | "professional_search_report_downloaded"
  | "professional_search_report_download_failed"
  // post-purchase signup
  | "professional_search_signup_submitted"
  | "professional_search_signup_succeeded"
  | "professional_search_signup_failed"
  // engagement
  | "professional_search_firm_tracked"
  | "professional_search_top_n_tracked"
  | "professional_search_marketplace_match_clicked"
  // misc
  | "professional_search_lang_toggled"
  | "professional_search_my_searches_viewed";

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

export function trackOnboardingEvent(
  event: OnboardingEvent,
  properties: Record<string, unknown> = {},
) {
  trackMixpanelEvent(event, {
    funnel: "check_onboarding",
    ...properties,
  });
}

export function trackProfessionalSearchEvent(
  event: ProfessionalSearchEvent,
  properties: Record<string, unknown> = {},
) {
  trackMixpanelEvent(event, {
    funnel: "professional_search",
    ...properties,
  });
}

export function trackSubscriptionEvent(
  event: SubscriptionEvent,
  properties: Record<string, unknown> = {},
) {
  trackMixpanelEvent(event, {
    funnel: "subscription",
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
