# Data Room Batch 31

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 31 manifest

This batch captures the remaining higher-signal employment legal and admin overflow: NDA packets, PTO correspondence, I-983 admin email, signature-only packets, check imagery, a tax information form, and a Yangtze EIN application.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `rai_nda_drpecker` | `employment/Rai/6ee18925-9e2b-40e2-b442-a956c4100c28.pdf` | DR.PECKER NDA packet | `non_disclosure_agreement` |
| `rai_nda_thunderbirds` | `employment/Rai/804ccf02-db8a-48f0-bdb7-a16f409c40bc.pdf` | THUNDERBIRDS NDA packet | `non_disclosure_agreement` |
| `rai_nda_rai` | `employment/Rai/b9b71b3f-c562-4260-b628-784ff3f983fb.pdf` | RAI NDA packet | `non_disclosure_agreement` |
| `rai_pto_request` | `employment/Rai/Request for PTO and Floating Holiday Utilization 924  1011.pdf` | PTO request and response email | `employment_correspondence` |
| `vcv_i983_review_request` | `employment/VCV/Gmail - Request for Review and Confirmation of I-983 and Compliance Information.pdf` | I-983 review request email | `i983` |
| `vcv_signature_pages` | `employment/VCV/Signature Pages.pdf` | signature-only employment packet pages | `signature_page` |
| `wolff_blank_stock_check` | `employment/Wolff & Li/blank_stock_check_payment.pdf` | stock check or payment image | `check_image` |
| `rai_morningstar_article` | `employment/Rai/Glyde Digital Announces RAI Inc. Secures $45 Million in Strategic Investments to Advance XR and AI Innovation _ Morningstar.pdf` | employer-related external article | `news_article` |
| `tax_2024_1099_int` | `Tax/2024/document.pdf` | 2024 interest-income tax form | `1099` |
| `yangtze_ss4_application` | `Yangtze Capital/Yangtze Capital.pdf` | SS-4 EIN application for Yangtze Capital | `ein_application` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `1/10`
- Surfaced gaps:
  - Rai NDA packets were unsupported because the files were UUID-named PDFs with no typed filename anchors
  - VCV signature pages, Wolff blank check imagery, and the Morningstar article were unsupported
  - the generic `Tax/2024/document.pdf` file was not recognized as a `1099`
  - the Yangtze SS-4 EIN application only resolved by OCR or manual inspection, not fast-path intake

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- NDA packets, signature-only employment pages, check imagery, news coverage, the generic tax form path, and the Yangtze EIN application now land on stable typed families.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 31`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 31 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-31-35`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-31-35/20260328T221247Z-01`
  - focused tests: `56 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether NDA packets should stay in their own agreement family or collapse into a broader employment-contract lineage.
