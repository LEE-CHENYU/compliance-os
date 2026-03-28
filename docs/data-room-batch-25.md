# Data Room Batch 25

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 25 manifest

This batch turns the remaining uncovered STEM OPT I-983 variants and templates into explicit typed records so older or partial training-plan artifacts remain searchable and version-aware.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `i983_sample_instructions` | `stem opt/i983/Instructions/I-983 Sample.pdf` | sample I-983 reference file | `i983` |
| `i983_blank_instructions` | `stem opt/i983/Instructions/i983.pdf` | blank I-983 reference file | `i983` |
| `clinipulse_i983_pages_1_4` | `stem opt/i983/clinipulse/i983-1-4-pages.pdf` | partial Clinipulse I-983 pages 1 to 4 | `i983` |
| `clinipulse_i983_pages_2_4` | `stem opt/i983/clinipulse/i983-page-2-4.pdf` | partial Clinipulse I-983 pages 2 to 4 | `i983` |
| `clinipulse_i983_page5` | `stem opt/i983/clinipulse/i983-page-5.pdf` | partial Clinipulse I-983 page 5 | `i983` |
| `clinipulse_i983_template` | `stem opt/i983/clinipulse/i983-template.pdf` | Clinipulse I-983 template | `i983` |
| `general_i983_template` | `stem opt/i983/i983-template.pdf` | general I-983 template | `i983` |
| `vcv_i983_page5_241001` | `stem opt/i983/vcv/i983-241001-page5.pdf` | VCV page-5 I-983 variant | `i983` |
| `vcv_i983_ink_signed` | `stem opt/i983/vcv_outdated_versions/I983-ink signed.pdf` | ink-signed archived VCV I-983 | `i983` |
| `vcv_i983_1031` | `stem opt/i983/vcv_outdated_versions/i983-1031.pdf` | October 31 archived VCV I-983 | `i983` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The uncovered STEM OPT overflow files all land cleanly on the canonical `i983` family.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required. This batch was materialized and validated as a clean I-983 overflow-history slice.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 25`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 25 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-21-25`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-21-25/20260328T213608Z-04`
  - focused tests: `51 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether partial page-only `i983` artifacts should stay grouped under the main `i983` family or get a narrower subtype for page-fragment history.
