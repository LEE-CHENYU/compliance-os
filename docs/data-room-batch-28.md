# Data Room Batch 28

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 28 manifest

This batch turns the last uncovered I-983 overflow set into explicit typed records, including both archived forms and employment-side email requests that are materially about I-983 updates.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `vcv_i983_edited` | `stem opt/i983/vcv_outdated_versions/i983_edited.pdf` | edited VCV I-983 archive | `i983` |
| `vcv_i983_edited_1026` | `stem opt/i983/vcv_outdated_versions/i983_edited_1026.pdf` | October 26 VCV I-983 archive | `i983` |
| `vcv_i983_edited_highlights` | `stem opt/i983/vcv_outdated_versions/i983_edited_with_highlights.pdf` | highlighted VCV I-983 archive | `i983` |
| `vcv_i983_copy_cn` | `stem opt/i983/vcv_outdated_versions/i983_副本.pdf` | archived I-983 copy | `i983` |
| `wolff_i983_pages_2_4_signed` | `stem opt/i983/wolff-and-li/i983-wolff-and-li-2-4-signed.pdf` | signed page-set I-983 archive | `i983` |
| `wolff_i983_pages_2_4` | `stem opt/i983/wolff-and-li/i983-wolff-and-li-2-4.pdf` | page-set I-983 archive | `i983` |
| `wolff_i983_page_1` | `stem opt/i983/wolff-and-li/i983-wolff-and-li-page1.pdf` | page-1 I-983 fragment | `i983` |
| `wolff_i983_full` | `stem opt/i983/wolff-and-li/i983-wolff-and-li.pdf` | full Wolff & Li I-983 | `i983` |
| `rai_i983_update_request` | `employment/Rai/Gmail - Urgent_ STEM OPT Employment End Date and Form I-983 Update Request.pdf` | employment-side I-983 update request | `i983` |
| `rai_i983_material_change_request` | `employment/Rai/LionMail Mail - Urgent_ Request for Guidance on Reporting Material Changes to Form I-983.pdf` | employment-side I-983 material-change request | `i983` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The remaining I-983 overflow records already resolve into the canonical `i983` family.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No batch-specific code changes were required. This slice is now explicitly tracked and validated as I-983 overflow history.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 28`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 28 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-26-30`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-26-30/20260328T215409Z-01`
  - focused tests: `54 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether email wrappers around I-983 requests should remain under the I-983 family or split into a narrower STEM OPT correspondence subtype.
