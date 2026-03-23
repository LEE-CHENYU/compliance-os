═══════════════════════════════════════════════════════════════════════════════
QUARTERLY DOCUMENT GENERATOR - USER GUIDE
Greenfield Capital LLC
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS SCRIPT DOES
═══════════════════════════════════════════════════════════════════════════════

The script `generate_quarterly_documents.py` automatically generates properly
formatted LLC capital contribution and distribution documents from your Schwab
transaction CSV exports.

It creates ONE consolidated document per quarter containing ALL transactions
for that quarter, maximizing liability protection with proper legal language.


DOCUMENTS GENERATED
═══════════════════════════════════════════════════════════════════════════════

For each quarter with cash contributions:
  • Capital Contribution Written Consent (all cash contributions consolidated)

For each quarter with position/equity transfers:
  • Position Transfer Written Consent (all in-kind securities consolidated)

For each quarter with distributions:
  • Distribution Authorization (all distributions consolidated)

Summary:
  • Quarterly Activity Summary (overview of all quarters)


HOW TO USE
═══════════════════════════════════════════════════════════════════════════════

STEP 1: Export your transaction data from Schwab
  1. Log into your Schwab account
  2. Go to Accounts → History
  3. Select date range (e.g., full year or specific quarter)
  4. Export as CSV
  5. Save to your accounting folder

STEP 2: Run the script

  Option A - With filename as argument:
    python3 generate_quarterly_documents.py YourFile.csv

  Option B - Interactive (it will prompt you):
    python3 generate_quarterly_documents.py

  Option C - Use default filename:
    python3 generate_quarterly_documents.py
    (Press Enter when prompted, uses default CSV name)

STEP 3: Review generated documents

  All documents are saved to: Generated_Quarterly_Documents/

  Files created:
    • CapitalContribution_Consent_Q1-2025.txt
    • CapitalContribution_Consent_Q2-2025.txt
    • CapitalContribution_Consent_Q3-2025.txt
    • Distribution_Authorization_Q2-2025.txt
    • Distribution_Authorization_Q3-2025.txt
    • Quarterly_Activity_Summary.txt

STEP 4: Sign and file the documents

  For each document:
    1. Review all amounts and dates for accuracy
    2. Verify against bank statements
    3. Print the document
    4. Sign and date where indicated
    5. File in your LLC minute book/binder
    6. Keep electronic copies backed up
    7. Provide to tax preparer at year-end


WHAT THE SCRIPT IDENTIFIES
═══════════════════════════════════════════════════════════════════════════════

CASH CAPITAL CONTRIBUTIONS (Money IN to LLC):
  ✓ MoneyLink transfers from personal accounts
  ✓ Wire transfers received
  ✓ Cashier's checks deposited
  ✓ Journal transfers FROM other accounts (cash)

POSITION/EQUITY TRANSFERS (Securities IN to LLC):
  ✓ Journaled Shares transactions (incoming positions)
  ✓ Stocks, ETFs, bonds, Treasury securities
  ✓ Calculates fair market value (quantity × price)
  ✓ Documents as in-kind capital contributions

DISTRIBUTIONS (Money OUT from LLC):
  ✓ Journal transfers TO other accounts
  ✓ MoneyLink transfers out (if any)


EXAMPLE OUTPUT
═══════════════════════════════════════════════════════════════════════════════

Running: python3 generate_quarterly_documents.py transactions.csv

Output:
  ✓ Parsed 163 transactions
  ✓ Found 13 cash capital contribution transactions
  ✓ Found 19 position/equity transfer transactions
  ✓ Found 2 distribution transactions

  Cash contributions by quarter:
    Q1-2025: 6 transactions, $80,861.66
    Q2-2025: 4 transactions, $18,720.78
    Q3-2025: 3 transactions, $53,820.00

  Position transfers by quarter:
    Q2-2025: 19 positions, $12,111,210.49 FMV

  Distributions by quarter:
    Q2-2025: 1 transactions, $3,900.00
    Q3-2025: 1 transactions, $22,620.00

  Generating documents...
  ✓ Q1-2025: 6 cash contributions, $80,861.66
  ✓ Q2-2025: 4 cash contributions, $18,720.78
  ✓ Q3-2025: 3 cash contributions, $53,820.00
  ✓ Q2-2025: 19 positions transferred, $12,111,210.49 FMV
  ✓ Q2-2025: 1 distribution, $3,900.00
  ✓ Q3-2025: 1 distribution, $22,620.00

  COMPLETE! All documents saved to: Generated_Quarterly_Documents/


CUSTOMIZATION
═══════════════════════════════════════════════════════════════════════════════

To modify LLC information, edit the top of generate_quarterly_documents.py:

  LLC_NAME = "Greenfield Capital LLC"
  LLC_STATE = "Wyoming"
  LLC_EIN = "12-3456789"
  LLC_FORMATION_DATE = "June 16, 2023"
  MEMBER_NAME = "Alex Zhang"
  LLC_BANK = "Charles Schwab Bank"

Save the file after making changes.


LEGAL PROTECTIONS INCLUDED
═══════════════════════════════════════════════════════════════════════════════

Each document includes:

For Cash Capital Contributions:
  ✓ Wyoming statutory authority (W.S. § 17-29-407)
  ✓ Clear equity vs. debt documentation
  ✓ Fraudulent transfer defenses
  ✓ Pre-claim planning representations
  ✓ Solvency certifications
  ✓ Proper journal entries for bookkeeping
  ✓ Tax treatment documentation (IRC § 721)

For Position/Equity Transfers (In-Kind Contributions):
  ✓ Wyoming statutory authority (W.S. § 17-29-407)
  ✓ Full listing of all securities with quantities and values
  ✓ Fair market valuation methodology
  ✓ IRC § 721 non-recognition treatment
  ✓ Carryover basis documentation (tax basis tracking)
  ✓ IRC § 704(c) built-in gain/loss allocations
  ✓ Title transfer representations
  ✓ Unencumbered property certifications
  ✓ Fraudulent transfer defenses
  ✓ Arm's length transaction documentation
  ✓ Proper journal entries (debit: investment securities)

For Distributions:
  ✓ Distribution authorization under W.S. § 17-29-405
  ✓ Wyoming solvency tests (balance sheet & cash flow)
  ✓ Surplus test with capital account tracking
  ✓ Creditor prejudice defenses
  ✓ Fraudulent transfer defenses
  ✓ Discretionary nature of distributions
  ✓ Proper journal entries


QUARTERLY WORKFLOW
═══════════════════════════════════════════════════════════════════════════════

EACH QUARTER (every 3 months):

  1. Export transactions from Schwab (CSV format)

  2. Run script:
     python3 generate_quarterly_documents.py latest_export.csv

  3. Review documents in Generated_Quarterly_Documents/

  4. Verify amounts match bank statements

  5. Print, sign, and date each document

  6. File in LLC minute book by quarter:
     • /LLC_Records/Minutes_and_Resolutions/2025/Q1/
     • /LLC_Records/Minutes_and_Resolutions/2025/Q2/
     • /LLC_Records/Minutes_and_Resolutions/2025/Q3/
     • /LLC_Records/Minutes_and_Resolutions/2025/Q4/

  7. Attach bank statements as supporting documentation

  8. Update capital account ledger


ANNUAL WORKFLOW
═══════════════════════════════════════════════════════════════════════════════

AT YEAR END (December 31):

  1. Export full year transactions

  2. Run script to generate all quarterly documents

  3. Review Quarterly_Activity_Summary.txt for year overview

  4. Verify all quarters have signed documents

  5. Provide copies to tax preparer:
     • All Capital Contribution Consents
     • All Distribution Authorizations
     • Quarterly Activity Summary
     • Bank statements

  6. File Wyoming Annual Report (due annually)

  7. Pay Wyoming Annual License Tax ($47 minimum)

  8. File federal tax return (Form 1065 + K-1)


TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

ERROR: "File not found"
  → Check that the CSV file path is correct
  → Make sure you're in the accounting directory
  → Use full path if needed: /Users/devuser/accounting/file.csv

ERROR: "No contributions found"
  → Verify the CSV is from Schwab (correct format)
  → Check date range includes actual transactions
  → Ensure CSV has the correct columns

Script doesn't recognize a transaction:
  → Check transaction description in CSV
  → Contributions must be: MoneyLink IN, Wire, Funds Received, or Journal FRM
  → Distributions must be: Journal TO or MoneyLink OUT
  → Edit script's identify_contributions() or identify_distributions() if needed

Wrong amounts showing:
  → Verify CSV format matches expected format
  → Check for missing $ signs or commas in amounts
  → Review transaction descriptions for accuracy


FILE LOCATIONS
═══════════════════════════════════════════════════════════════════════════════

Current setup:
  Working directory:       /Users/devuser/accounting/
  Script location:         generate_quarterly_documents.py
  Template library:        Quarterly_Capital_Contribution_Distribution_Templates.txt
  Output directory:        Generated_Quarterly_Documents/
  Transaction exports:     *.csv (Schwab exports)


IMPORTANT NOTES
═══════════════════════════════════════════════════════════════════════════════

✓ Run this EVERY QUARTER to maintain corporate formalities
✓ Always review generated documents before signing
✓ Keep both electronic and physical copies
✓ Store original signed documents for minimum 7 years (IRS requirement)
✓ Provide copies to tax preparer annually
✓ These documents help maintain LLC liability protection
✓ Contemporaneous documentation (done at time of transaction) is strongest
✓ Never backdate documents - use actual dates
✓ Attach bank statements as supporting evidence


SUPPORT
═══════════════════════════════════════════════════════════════════════════════

For questions about:
  • Script usage: Review this README
  • Legal compliance: Consult a Wyoming business attorney
  • Tax treatment: Consult a CPA or tax advisor
  • LLC requirements: Wyoming Secretary of State (sos.wyo.gov)


═══════════════════════════════════════════════════════════════════════════════
Last Updated: October 8, 2025
Version: 2.0 (Consolidated quarterly documents)
═══════════════════════════════════════════════════════════════════════════════
