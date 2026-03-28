# Data Room Batch 05

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 05 manifest

This batch resolves identity and travel continuity for F-1 history while anchoring overflow personal archive and tax records that matter for retrieval and cross-document checks.

| Label | File | Intended use | Current classification result |
| --- | --- | --- | --- |
| `i20_fa_2025` | `i20/I-20_Li_Chenyu_ FA 2025.pdf` | current school I-20 anchor | `i20` |
| `i20_cu_travel_2022` | `i20/cu_travel_22.pdf` | travel-signed I-20 history | `i20` |
| `i20_cu_travel_2023` | `i20/cu_travel_23.pdf` | updated travel-signed I-20 history | `i20` |
| `i20_cu_opt` | `i20/cu_opt.pdf` | OPT-period I-20 history | `i20` |
| `i94_recent` | `I94 - 1019 print.pdf` | latest arrival/departure record | `i94` |
| `passport_identity` | `passport.jpeg` | passport identity page | `passport` |
| `ead_archive` | `Personal Info Archive/EAD_expired.pdf` | archived EAD identity/work-authorization record | `ead` |
| `w2_2024` | `Tax/2024/Form_W-2_Tax_Year_2024.pdf` | wage identity and tax-year anchor | `w2` |
| `tax_return_2024` | `Tax/2024/2024_TaxReturn.pdf` | annual return baseline | `tax_return` |
| `form_1042s_2025` | `Tax/2025/1042S - 2025_2026-03-10_619.PDF` | withholding overflow record | `1042s` |

## Batch 05 priority order

1. Identity anchors first: `passport`, `i94`, `i20`, and `ead` because these drive the highest-value person/travel consistency checks.
2. I-20 history second: prioritize current + travel-signed timeline records so review context reflects longitudinal status evidence.
3. Tax overflow third: align `w2`, `tax_return`, and `1042s` to preserve tax-year continuity and retrieval quality.
4. Remaining low-signal personal archive documents stay deferred unless they unlock a current review or retrieval gap.

## Batch 05 modeling and review updates

Batch 05 adds extraction normalization and `data_room` review coverage for identity/travel/tax-overflow families.

Observed extraction fields now include:

- `i20`: student name, program end date, travel signature date
- `i94`: class of admission, most recent entry date, admit-until date
- `passport`: full name, date of birth, expiration date
- `ead`: full name, date of birth, card expiry
- `w2`, `tax_return`, and `1042s`: tax-year and identity fields used for consistency checks

Cross-document checks now include:

- I-20 student name ↔ passport full name
- I-20 student name ↔ EAD full name
- passport date of birth ↔ EAD date of birth
- passport full name ↔ W-2 employee name
- passport full name ↔ 1042-S recipient name
- W-2 tax year ↔ tax return tax year
- 1042-S tax year ↔ tax return tax year
- I-94 class of admission ↔ expected F-1 when I-20 evidence is present

## Validation

Focused Batch 05 regression suite:

- `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_checks_router_v2.py -q`

Required loop validation command:

- `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 05 --run-validation-hooks --json --log-root logs/data-room-batch-loop-agent-validate`

## Current batch blockers

None.

## Deferred backlog

1. Add dedicated support for visa-stamp-specific extraction and checks if `visa.jpeg` becomes a required control artifact.
2. Expand identity coverage to driver's license and SSN card records when those artifacts become required by a concrete check workflow.
3. Keep broader personal-archive cleanup and non-compliance educational records outside the blocking Batch 05 scope.

## Next queue

1. Keep Batches 01-05 stable under focused validation hooks.
2. Continue platform-level retrieval and family heuristics only when tied to a concrete regression.
