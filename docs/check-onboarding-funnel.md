# Check Onboarding Funnel

This funnel tracks the standard check onboarding flow across `student`, `stem_opt`, and `entity`.

## Canonical Funnel

1. `onboarding_track_select_viewed`
2. `onboarding_track_selected`
3. `onboarding_intake_viewed`
4. `onboarding_check_created`
5. `onboarding_upload_viewed`
6. `onboarding_document_uploaded`
7. `onboarding_review_phase_viewed` with `phase=followup` or `phase=snapshot`
8. `onboarding_results_viewed`
9. `onboarding_save_clicked`

## Key Properties

- `funnel=check_onboarding`
- `check_track`
- `check_id`
- `doc_type`
- `required`
- `phase`
- `stage`

## Recommended Mixpanel Reports

### Main Funnel

Use these steps:

1. `onboarding_track_select_viewed`
2. `onboarding_track_selected`
3. `onboarding_check_created`
4. `onboarding_document_uploaded`
5. `onboarding_results_viewed`
6. `onboarding_save_clicked`

Break down by:

- `check_track`
- `stage` for `stem_opt`

### Upload Conversion

Funnel:

1. `onboarding_upload_viewed`
2. `onboarding_document_uploaded`
3. `onboarding_results_viewed`

Break down by:

- `check_track`
- `doc_type`
- `required`

### Review Friction

Insights or funnel on:

- `onboarding_review_phase_viewed`
- `onboarding_followup_answered`
- `onboarding_results_viewed`

Break down by:

- `check_track`
- `phase`

## Implementation Files

- [frontend/src/lib/analytics.ts](/Users/lichenyu/compliance-os/frontend/src/lib/analytics.ts)
- [frontend/src/app/check/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/page.tsx)
- [frontend/src/app/check/student/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/student/page.tsx)
- [frontend/src/app/check/student/upload/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/student/upload/page.tsx)
- [frontend/src/app/check/student/review/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/student/review/page.tsx)
- [frontend/src/app/check/stem-opt/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/stem-opt/page.tsx)
- [frontend/src/app/check/stem-opt/upload/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/stem-opt/upload/page.tsx)
- [frontend/src/app/check/stem-opt/review/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/stem-opt/review/page.tsx)
- [frontend/src/app/check/entity/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/entity/page.tsx)
- [frontend/src/app/check/entity/upload/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/entity/upload/page.tsx)
- [frontend/src/app/check/entity/review/page.tsx](/Users/lichenyu/compliance-os/frontend/src/app/check/entity/review/page.tsx)
