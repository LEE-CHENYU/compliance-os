# Form 8843 GTM Funnel

This funnel tracks the public Form 8843 acquisition path from landing through first downstream document upload.

## Canonical Funnel

1. `form_8843_gtm_landing_viewed`
2. `form_8843_gtm_generate_succeeded`
3. `form_8843_gtm_auth_succeeded`
4. `form_8843_gtm_download_completed`
5. `form_8843_gtm_onboarding_cta_clicked`
6. `form_8843_gtm_check_created`
7. `form_8843_gtm_document_uploaded`

## Event Notes

- `form_8843_gtm_step_viewed` and `form_8843_gtm_step_completed` are diagnostic events for wizard dropoff by step.
- `form_8843_gtm_signin_prompt_viewed` and `form_8843_gtm_signin_cta_clicked` measure the conversion point between anonymous generation and account creation.
- `form_8843_gtm_check_path_inferred` tells us whether the user was routed into `student` or `stem_opt`.
- `form_8843_gtm_upload_viewed` and `form_8843_gtm_review_continued` measure progress after onboarding begins.

## Shared Properties

All 8843 GTM events include:

- `funnel=form_8843_gtm`
- `source=form8843`

Common event-specific properties include:

- `order_id`
- `signed_in`
- `step_index`
- `step_name`
- `auth_mode`
- `auth_method`
- `onboarding_path`
- `check_track`
- `check_id`
- `doc_type`
- `required`

## Recommended Mixpanel Breakdowns

- By `signed_in` on `form_8843_gtm_landing_viewed`
- By `step_name` on `form_8843_gtm_step_completed`
- By `auth_method` on `form_8843_gtm_auth_succeeded`
- By `onboarding_path` on `form_8843_gtm_onboarding_cta_clicked`
- By `check_track` on `form_8843_gtm_check_created`
- By `doc_type` on `form_8843_gtm_document_uploaded`

## Implementation Files

- [frontend/src/lib/analytics.ts](/Users/lichenyu/compliance-os/frontend/src/lib/analytics.ts)
- [frontend/src/app/form-8843/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/form-8843/page.tsx)
- [frontend/src/components/form8843/OnboardingWizard.tsx](/Users/lichenyu/compliance-os/frontend/src/components/form8843/OnboardingWizard.tsx)
- [frontend/src/app/form-8843/success/SuccessContent.tsx](/Users/lichenyu/compliance-os/frontend/src/app/form-8843/success/SuccessContent.tsx)
- [frontend/src/app/login/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/login/page.tsx)
- [frontend/src/app/check/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/page.tsx)
- [frontend/src/app/check/student/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/student/page.tsx)
- [frontend/src/app/check/stem-opt/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/stem-opt/page.tsx)
- [frontend/src/app/check/student/upload/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/student/upload/page.tsx)
- [frontend/src/app/check/stem-opt/upload/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/stem-opt/upload/page.tsx)
