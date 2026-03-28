# Data Room Batch 18

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 18 manifest

This batch targets financial-support overflow that is still outside the typed data-room path: collection letters, receipts, bank-support exports, and duplicate tax or wage statements.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `debt_clearance_letter` | `Lease/Collection/Debt Clearence.pdf` | debt-clearance support letter | `debt_clearance_letter` |
| `collection_correspondence` | `Lease/Collection/RE CDR Correspondence 0004626832 LICHENYU.pdf` | collections correspondence | `collection_notice` |
| `payment_receipt_one` | `Invoice/Payment Receipt.pdf` | payment receipt | `payment_receipt` |
| `payment_receipt_two` | `Invoice/Payment Receipt-2.pdf` | payment receipt | `payment_receipt` |
| `tax_bank_document_a` | `Tax/2024/bank_document_-2819197501764181827.pdf` | bank-support tax attachment | `bank_statement` |
| `tax_bank_document_b` | `Tax/2024/bank_document_7521979570670228494.pdf` | bank-support tax attachment | `bank_statement` |
| `w2_bank_document_a` | `W2/bank_document_-1954082152911695008.pdf` | wage-folder bank-support attachment | `bank_statement` |
| `w2_bank_document_b` | `W2/bank_document_7521979570670228494.pdf` | wage-folder bank-support attachment | `bank_statement` |
| `w2_folder_2023` | `W2/Form_W-2_Tax_Year_2023.pdf` | duplicate 2023 wage statement | `w2` |
| `treasurydirect_message` | `Personal Finance/A Message from TreasuryDirect.pdf` | TreasuryDirect account message | `bank_account_application` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `2/10`
- Already strong:
  - `w2`
  - `bank_account_application`
- Surfaced gaps:
  - debt-clearance and collection correspondence were unsupported
  - payment receipts were unsupported
  - `bank_document_*.pdf` attachments were either unclassified or drifting into `identity_document`

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- This batch now classifies cleanly across:
  - debt-clearance and collection notices
  - payment receipts
  - bank-support statements in tax and W-2 folders

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 18`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 18 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-16-20`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-16-20/20260328T183154Z-03`
  - focused tests: `51 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Pull these financial-support families into cross-document review only when a concrete debt, payment, or balance workflow needs them.
