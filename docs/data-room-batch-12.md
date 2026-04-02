# Data Room Batch 12

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 12 manifest

This batch covers company-access artifacts that matter for operational continuity but were still untyped: payment-platform records, public keys, recovery codes, and one filing artifact.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `alipay_service_agreement` | `公司信息/支付宝支付服务合同.pdf` | payment-service agreement | `payment_service_agreement` |
| `alipay_account_record` | `公司信息/支付宝平台账户.JPG` | payment-platform account screenshot | `payment_account_record` |
| `bank_account_record` | `公司信息/银行账户.JPG` | company bank-account screenshot | `bank_account_record` |
| `alipay_public_key_alt` | `公司信息/alipayPublicKey_RSA2 2.txt` | payment-platform public key | `public_key` |
| `alipay_public_key_business` | `公司信息/alipayPublicKey_RSA2(business).txt` | business public key | `public_key` |
| `alipay_public_key_new` | `公司信息/alipayPublicKey_RSA2-new.txt` | rotated public key | `public_key` |
| `stripe_backup_codes` | `公司信息/stripe_backup_code.txt` | Stripe recovery codes | `recovery_codes` |
| `shopify_recovery_codes` | `BSGC/shopify_recovery_codes.txt` | Shopify recovery codes | `recovery_codes` |
| `mercury_recovery_codes` | `Yangtze Capital/mercury-backup-codes-fretin13gmailcom.pdf` | Mercury backup codes | `recovery_codes` |
| `yangtze_initial_filing` | `Yangtze Capital/3-5-26 - null - Initial Filing - Yangtze Capital.pdf` | company filing artifact | `company_filing` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Remaining misses:
  - `payment_service_agreement`
  - `payment_account_record`
  - `bank_account_record`
  - `public_key`
  - `recovery_codes`
  - `company_filing`

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Company-access artifacts now classify cleanly across payment-service agreements, account screenshots, public keys, recovery codes, and the Yangtze filing artifact

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 12`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 12 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-11-15`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-11-15/20260328T161804Z-02`
  - focused tests: `48 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Expand retrieval or redaction policy for `public_key` and `recovery_codes` only if those sensitive artifacts need specialized handling downstream.
