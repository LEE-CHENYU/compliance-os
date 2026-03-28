# Data Room Batch 17

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 17 manifest

This batch focuses on STEM OPT admin and filing-support material that is not itself the core signed I-983: confirmations, instructions, guides, final evaluations, and employer-support artifacts.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `stem_i94_website_print` | `stem opt/I94 - Official Website - 20230919.pdf` | official I-94 printout | `i94` |
| `stem_order_confirmation` | `stem opt/Order Confirmation.pdf` | purchase or filing confirmation | `order_confirmation` |
| `stem_guide_cn` | `stem opt/STEM OPT申请完整攻略（含I-983表格填写指南）.pdf` | STEM OPT guidance packet | `immigration_reference` |
| `i983_sample_filled` | `stem opt/i983/Instructions/I-983samplefilled.pdf` | sample completed I-983 | `immigration_reference` |
| `i983_instructions` | `stem opt/i983/Instructions/i983Instructions.pdf` | I-983 instruction guide | `immigration_reference` |
| `harvard_i983_guide` | `stem opt/i983/Instructions/Harvard Administrator_ I-983 Guide_0.pdf` | school administrator I-983 guide | `immigration_reference` |
| `claudius_final_evaluation` | `stem opt/i983/claudius/Final Evaluation OPT.pdf` | final evaluation for STEM OPT | `final_evaluation` |
| `vcv_name_change_notice` | `stem opt/i983/vcv/VCV Digital Infra Alpha name change to VCV Digital Infrastructure.pdf` | employer name-change support notice | `name_change_notice` |
| `stem_employer_letter` | `stem opt/letter/stemoptemployerletter.pdf` | STEM OPT employer letter | `employment_letter` |
| `stem_retain_proof` | `stem opt/retain the proof.png` | filing or submission proof | `filing_confirmation` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `2/10`
- Already strong:
  - `i94`
  - `employment_letter`
- Surfaced gaps:
  - guidance and instruction packets were either unclassified or collapsing into `i983`
  - `Final Evaluation OPT.pdf` was not being recognized as `final_evaluation`
  - the VCV employer rename notice was not being recognized as `name_change_notice`
  - `retain the proof.png` had no family and was left unsupported

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- This batch now classifies cleanly across:
  - STEM OPT guidance and instruction packets as `immigration_reference`
  - final evaluations
  - employer name-change support
  - submission-proof artifacts as `filing_confirmation`

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 17`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 17 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-16-20`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-16-20/20260328T183154Z`
  - focused tests: `51 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Treat STEM OPT instructions and filing confirmations as retrieval/context support unless a concrete review flow starts consuming them.
