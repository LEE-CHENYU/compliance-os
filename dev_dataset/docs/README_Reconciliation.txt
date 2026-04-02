═══════════════════════════════════════════════════════════════════════════════
ACCOUNT RECONCILIATION SYSTEM - USER GUIDE
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS SCRIPT DOES
═══════════════════════════════════════════════════════════════════════════════

The `reconcile_all_accounts.py` script performs comprehensive reconciliation
across ALL your accounts to verify that every capital contribution and
distribution is properly tracked and matched.

This ensures:
  ✓ No money is lost or unaccounted for
  ✓ Every withdrawal has a corresponding deposit
  ✓ Capital contributions are traced to their source
  ✓ Distributions are traced to their destination
  ✓ Position transfers are balanced
  ✓ Internal transfers are not double-counted


ACCOUNTS RECONCILED
═══════════════════════════════════════════════════════════════════════════════

The script automatically reconciles these 5 accounts:

1. CHK_1234 - Business Checking (Citibank)
   - Greenfield Capital LLC operating account
   - Contains owner contributions (Zelle deposits)
   - Contains distributions (teller withdrawals, cashier's checks)

2. CHK_5678 - Personal Checking (Citibank)
   - Personal account of Alex Zhang
   - MoneyLink transfers to investment accounts
   - Wire receipts and personal expenses

3. boa_stmt.csv - Personal Checking (Bank of America)
   - Personal account of Alex Zhang
   - MoneyLink transfers to personal brokerage
   - Zelle payments and personal transactions

4. XXX567 - LLC Brokerage (Schwab)
   - Greenfield Capital LLC investment account
   - Receives capital contributions (MoneyLink, cashier's checks, wires)
   - Makes distributions (Journal transfers to personal brokerage)
   - Position transfers (in-kind securities contributions)

5. XXX890 - Personal Brokerage (Schwab)
   - Personal investment account of Alex Zhang
   - MoneyLink transfers from checking accounts
   - Position transfers to LLC (securities contributions)
   - Distributions from LLC via Journal transfers


HOW TO USE
═══════════════════════════════════════════════════════════════════════════════

STEP 1: Ensure all CSV files are in the accounting directory

  Required files:
    - CHK_1234_CURRENT_VIEW.csv
    - CHK_5678_CURRENT_VIEW.csv
    - boa_stmt.csv
    - Limit_Liability_Company_XXX239_Transactions_20251008-155741.csv
    - Individual_XXX619_Transactions_20251008-172052.csv

STEP 2: Run the reconciliation script

  Command:
    python3 reconcile_all_accounts.py

  The script will:
    1. Parse all 5 account CSV files
    2. Classify every transaction by type
    3. Match related transactions across accounts
    4. Run reconciliation checks
    5. Generate comprehensive reports

STEP 3: Review the generated reports

  All reports are saved to: Reconciliation_Reports/

  Files generated:
    - Master_Transaction_Ledger.csv
    - Matched_Transactions_Report.txt
    - Unmatched_Transactions_Report.txt
    - Entity_Capital_Account_Summary.txt
    - Reconciliation_Summary.txt


TRANSACTION MATCHING
═══════════════════════════════════════════════════════════════════════════════

The script automatically matches:

MONEYLINK TRANSFERS
  - Checking account withdrawals → Brokerage account deposits
  - Brokerage account withdrawals → Checking account deposits
  - Matches by date (within 5 days) and exact amount
  - Examples:
    • CHK_5678 -$23,400 → XXX567 +$23,400
    • BOA -$10,530 → XXX890 +$10,530
    • XXX890 -$12,480 → CHK_5678 +$12,480

JOURNAL TRANSFERS
  - Between XXX890 (personal brokerage) and XXX567 (LLC brokerage)
  - Same-day transfers with matching amounts
  - Examples:
    • XXX890 -$22,620 → XXX567 +$22,620 (distribution)
    • XXX890 -$17,160 → XXX567 +$17,160 (contribution)

POSITION TRANSFERS
  - Securities transferred from personal to LLC
  - Matches by date, symbol, and quantity
  - Includes stocks, ETFs, Treasury securities
  - Examples:
    • INTC: XXX890 -1,195 shares → XXX567 +1,195 shares
    • Treasury Bills: XXX890 -25,000 → XXX567 +25,000

CASHIER'S CHECKS
  - Large cash withdrawals converted to cashier's checks
  - Matches withdrawal to multiple deposits
  - Example: $78,000 CRITICAL FINDING
    • CHK_1234 -$78,000 (02/27/2025 teller withdrawal)
    • XXX567 +$19,500 (cashier's check 02/28/2025)
    • XXX567 +$19,500 (cashier's check 03/03/2025)
    • XXX567 +$19,500 (cashier's check 03/03/2025)
    • XXX890 +$19,500 (cashier's check 02/27/2025)
    ✓ FULLY ACCOUNTED

INTERNAL CHECKING TRANSFERS
  - Between CHK_1234 and CHK_5678
  - Same-day or next-day transfers
  - Examples:
    • CHK_5678 -$39,000 → CHK_5678 +$39,000 (reversed)


REPORTS EXPLAINED
═══════════════════════════════════════════════════════════════════════════════

1. MASTER TRANSACTION LEDGER (CSV)

   A comprehensive list of ALL transactions across ALL accounts in
   chronological order.

   Columns:
     - Date: Transaction date
     - Account: Which account (CHK_1234, CHK_5678, BOA, XXX567, XXX890)
     - Amount: Positive = inflow, Negative = outflow
     - Type: Transaction classification
     - Description: Original transaction description
     - Match_ID: ID linking related transactions
     - Related_Account: Destination/source account
     - Symbol: For position transfers
     - Quantity: For position transfers
     - Notes: Additional information

   Uses:
     - Import into Excel/Google Sheets for analysis
     - Create pivot tables by account, quarter, type
     - Identify all transactions in a specific date range


2. MATCHED TRANSACTIONS REPORT (TXT)

   Shows groups of related transactions that were successfully matched.

   Format:
     MATCH GROUP #1 - ML0001
     ────────────────────────────────────────────
       2025-05-14 | CHK_1234 |    -4,500.00 | MONEYLINK_OUT
       2025-05-14 | XXX567   |     4,500.00 | MONEYLINK_IN
       NET: $0.00

   Each group shows:
     - All related transactions (source and destination)
     - Accounts involved
     - Amounts
     - Net total (should be $0.00 for balanced transfers)

   Uses:
     - Verify transfers completed correctly
     - Audit capital contributions and distributions
     - Confirm position transfers were received


3. UNMATCHED TRANSACTIONS REPORT (TXT)

   Lists transactions that could not be matched to a counterpart.

   These are typically:
     ✓ External income (salary, rent payments)
     ✓ External expenses (personal purchases, fees)
     ✓ Zelle payments (roommate splits, personal transfers)
     ✓ Wire fees
     ✓ Small cash withdrawals for personal use

   Action required:
     - Review for any missing large transfers
     - Verify unmatched contributions/distributions are explained
     - Most personal expenses should remain unmatched (expected)


4. ENTITY CAPITAL ACCOUNT SUMMARY (TXT)

   Quarterly breakdown of contributions and distributions by entity.

   Format:
     LLC XXX567 (Greenfield Capital LLC)
     ════════════════════════════════════════════
       Q1-2025:
         Contributions:  $  80,861.66
         Distributions:  $        0.00
         Net:            $  80,861.66

   Entities tracked:
     - LLC XXX567 (Greenfield Capital LLC)
     - Business Checking CHK_1234
     - Personal Brokerage XXX890

   Uses:
     - Track capital account changes quarterly
     - Verify contribution/distribution balances
     - Prepare for tax return (Form 1065, K-1)
     - Monitor cash flow by quarter


5. RECONCILIATION SUMMARY (TXT)

   Final pass/fail report of all reconciliation checks.

   Checks performed:
     ✓ MoneyLink Matched: All MoneyLink transfers have counterparts
     ✓ Journal Matched: All journal transfers balanced
     ✓ Cashiers Check 100K: $78,000 withdrawal fully accounted
     ✓ Position Transfers Balanced: All securities transferred match
     ✓ Contributions Sourced: All LLC contributions traced to source
     ✓ Distributions Traced: All distributions traced to destination

   Status:
     ✓ PASS = All transactions reconciled
     ✗ FAIL = Some transactions unmatched (review required)

   Statistics:
     - Total transactions parsed
     - Number of matched groups
     - Number of unmatched transactions
     - Breakdown by account


RECONCILIATION RESULTS
═══════════════════════════════════════════════════════════════════════════════

TYPICAL RECONCILIATION OUTPUT:

  Total Transactions: 939
  ─────────────────────────────────────────────
    CHK_1234 (Business):      84 transactions
    CHK_5678 (Personal Citi): 62 transactions
    BOA (Personal):          466 transactions
    XXX567 (LLC Brokerage):  163 transactions
    XXX890 (Personal Brok):  164 transactions

  Matched Groups: 49
  ─────────────────────────────────────────────
    MoneyLink transfers:      20 pairs
    Position transfers:       21 pairs
    Journal transfers:         6 pairs
    Cashier's checks:          1 group (4 deposits)
    Internal checking:         1 pair

  Reconciliation Status:
  ─────────────────────────────────────────────
    ✓ $78,000 cash withdrawal: FULLY ACCOUNTED
    ✓ Position transfers: 100% balanced
    ✓ MoneyLink transfers: 97.6% matched
    ✓ Journal transfers: 92.3% matched

  Unmatched: 204 transactions
  ─────────────────────────────────────────────
    Most are expected (personal Zelle, expenses, fees)
    Review report for any unexpected large amounts


KEY FINDINGS
═══════════════════════════════════════════════════════════════════════════════

1. $78,000 CASH WITHDRAWAL - FULLY RECONCILED

   Date: February 27, 2025
   Source: CHK_1234 (Business Checking)

   What happened:
     - Owner withdrew $78,000 cash from business checking
     - Converted to 4 cashier's checks of $19,500 each
     - Deposited into investment accounts:
       • $58,500 → LLC XXX567 (3 checks on 02/28 and 03/03)
       • $19,500 → Personal XXX890 (1 check on 02/27)

   Tax treatment:
     - $78,000 = Taxable distribution from business (Q1-2025)
     - $58,500 = Capital contribution to LLC (Q1-2025)
     - Net personal cash: $19,500 (used for personal investment)


2. POSITION TRANSFERS - $12.1 MILLION VERIFIED

   Date: May 1, 2025
   Source: XXX890 (Personal Brokerage)
   Destination: XXX567 (LLC Brokerage)

   All 19 securities matched perfectly:
     ✓ INTC: 1,195 shares
     ✓ PDD: 150 shares
     ✓ Treasury Securities: $12.0M value
     ✓ OXY: 1,483.879 shares
     ✓ ETFs and other positions

   Status: 100% reconciled


3. CAPITAL CONTRIBUTIONS SUMMARY

   LLC XXX567 Total Contributions: $153,402.44 (cash)
   ───────────────────────────────────────────────────
     Q1-2025: $80,861.66
       - MoneyLink from business checking: $7,020.78
       - Cashier's checks: $58,500.00
       - Wire from personal: $2,861.66
       - Journal from XXX890: $2,340.00

     Q2-2025: $18,720.78
       - MoneyLink from business: $7,020.78
       - Journal from XXX890: $11,700.00

     Q3-2025: $53,820.00
       - MoneyLink from personal: $46,800.00
       - Journal from XXX890: $7,020.00

   Position Transfers (Q2-2025): $12,111,210.49
   ───────────────────────────────────────────
     All securities from XXX890 → XXX567


4. DISTRIBUTIONS SUMMARY

   FROM LLC XXX567: $26,520.00
   ───────────────────────────────────────────────────
     Q2-2025: $3,900 (Journal to XXX890 on 04/07/2025)
     Q3-2025: $22,620 (Journal to XXX890 on 09/11/2025)

   FROM Business CHK_1234: $79,326.00
   ───────────────────────────────────────────────────
     Q1-2025: $78,000 (02/27/2025 - cashier's checks)
     Q2-2025: $780 (04/30/2025 - teller)
     Q3-2025: $546 (09/12/2025 - withdrawal)

   TOTAL DISTRIBUTIONS: $105,846.00


TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

ERROR: "File not found"
  → Ensure all 5 CSV files are in /Users/devuser/accounting/
  → Check file names match exactly (case-sensitive)
  → Use full paths if running from different directory

ERROR: "Total transactions parsed: 0"
  → Check CSV format is correct
  → Ensure files are not empty
  → Verify no encoding issues (should be UTF-8)

High number of unmatched transactions
  → Review Unmatched_Transactions_Report.txt
  → Check for large amounts that should have matches
  → Verify date ranges overlap between accounts
  → Personal expenses (Zelle, purchases) are expected to be unmatched

MoneyLink transfers not matching
  → Check date range (should be within 5 days)
  → Verify amounts match exactly
  → Look for typos in bank descriptions
  → May need to adjust matching tolerance in script

Position transfers not matching
  → Verify same symbol and date
  → Check quantity matches (fractional shares okay)
  → Ensure both "Journaled Shares" transactions are present


MAINTENANCE
═══════════════════════════════════════════════════════════════════════════════

MONTHLY: Export new transactions from all accounts
  - Update CSV files with latest data
  - Re-run reconciliation
  - Review for any unmatched large amounts

QUARTERLY: Review capital account summary
  - Verify contribution/distribution totals
  - Prepare quarterly LLC documents
  - Update capital account ledger

ANNUALLY: Full reconciliation for tax preparation
  - Export full year transactions
  - Run final reconciliation
  - Provide reports to tax preparer
  - File with Form 1065 documentation


FILE LOCATIONS
═══════════════════════════════════════════════════════════════════════════════

Working directory:     /Users/devuser/accounting/
Script location:       reconcile_all_accounts.py
Input files:           *.csv (5 account files)
Output directory:      Reconciliation_Reports/
Generated reports:     5 files (CSV and TXT)


TECHNICAL DETAILS
═══════════════════════════════════════════════════════════════════════════════

Transaction Types Classified:
  - POSITION_TRANSFER_IN/OUT: Securities transferred between accounts
  - JOURNAL_TRANSFER_IN/OUT: Cash journals between XXX890 ↔ XXX567
  - MONEYLINK_IN/OUT: ACH transfers to/from Schwab accounts
  - CASHIERS_CHECK_DEPOSIT/WITHDRAWAL: Cashier's check transactions
  - WIRE_IN/OUT: Wire transfers and fees
  - TELLER_WITHDRAWAL/DEPOSIT: Bank teller transactions
  - CHECKING_TRANSFER_IN/OUT: Between CHK_1234 ↔ CHK_5678
  - ZELLE_IN/OUT: Zelle payment network
  - INVESTMENT_ACTIVITY: Buys, sells, dividends (internal to brokerage)
  - EXTERNAL_INCOME/EXPENSE: Personal transactions

Matching Rules:
  - MoneyLink: ±5 days, exact amount match
  - Journal: Same day, exact amount match
  - Position: Same day, same symbol, same quantity
  - Cashier's: ±7 days, sum of deposits = withdrawal amount
  - Checking: ±1 day, exact amount match


SUPPORT & QUESTIONS
═══════════════════════════════════════════════════════════════════════════════

For questions about:
  • Script usage: Review this README
  • Tax implications: Consult with CPA or tax advisor
  • LLC compliance: Consult Wyoming business attorney
  • Brokerage accounts: Contact Charles Schwab support
  • Banking questions: Contact Citibank or Bank of America


═══════════════════════════════════════════════════════════════════════════════
Last Updated: October 8, 2025
Version: 1.0
═══════════════════════════════════════════════════════════════════════════════
