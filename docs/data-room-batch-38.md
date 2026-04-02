# Data Room Batch 38

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 38 manifest

This batch captures the remaining hiring portal, website-admin, and account-security screenshots plus one academic invitation email PDF.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `happyhunting_resume_board_1` | `Happyhunting Screenshot/51745372824_.pic.jpg` | hiring portal screenshot with resume variants | `employment_screenshot` |
| `happyhunting_resume_board_2` | `Happyhunting Screenshot/61745372830_.pic.jpg` | hiring portal screenshot with resume variants | `employment_screenshot` |
| `happyhunting_resume_board_3` | `Happyhunting Screenshot/71745372836_.pic.jpg` | hiring portal screenshot with resume variants | `employment_screenshot` |
| `happyhunting_resume_board_4` | `Happyhunting Screenshot/91745372843_.pic.jpg` | hiring portal screenshot with resume variants | `employment_screenshot` |
| `root_network_config_screenshot` | `Weixin Image_2025-07-02_213642_922.png` | network or IP-configuration screenshot | `system_configuration_screenshot` |
| `schwab_signature_code_screenshot` | `スクリーンショット 2025-04-17 午前11.49.19.png` | electronic-signature confirmation-code screen | `account_security_setup` |
| `veeup_network_config_screenshot` | `Veeup.cc/WechatIMG13.jpg` | website or server network-configuration screenshot | `system_configuration_screenshot` |
| `veeup_filing_guidance_screenshot` | `Veeup.cc/WechatIMG14.jpg` | website filing guidance or admin screenshot | `company_filing` |
| `veeup_filing_notice_screenshot` | `Veeup.cc/WechatIMG371.jpg` | website filing notice or confirmation screenshot | `company_filing` |
| `projectworld_invitation_email` | `Invitation to the projectWorld Congress in Computer Science Computer Engineering and Applied Computing.pdf` | academic conference invitation email | `event_invitation` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Surfaced gaps:
  - hiring portal screenshots, network-config screenshots, Veeup admin screenshots, and the conference invitation PDF were unsupported on the fast path
  - the intake layer lacked typed support for system-configuration screenshots and event-invitation emails

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Hiring screenshots, system-config screenshots, account-security setup screens, Veeup filing screenshots, and the invitation email now resolve to stable typed families.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 38`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 38 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-36-40`
  - Passing session: `logs/data-room-batch-loop-round-36-40/20260328T224019Z-01`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py -q`
  - Result: `58 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Validate and wire fast-path support for the remaining portal, network, and account-security screenshot slice.
