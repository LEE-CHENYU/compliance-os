"""CPA / tax engagement case template.

Derived from the Kaufman Rossin `data_room/` gold-standard structure
for a nonresident alien with a foreign-owned US disregarded entity
(BSGC LLC) triggering Form 5472 + pro forma 1120 reporting.

Section layout:
  0 — Case Summary (narrative + scope + issues brief)
  1 — Entity (formation docs, EIN, operating agreement)
  2 — Tax Returns (by year)
  3 — Income Documents (W-2, 1042-S, 1099-B, 1099-INT, 1098-T, year-end)
  4 — Tax Compliance Issues (memo)
  5 — Ledger Records (capital account, facts sheet)
  6 — Bank / Brokerage Statements (transactions, statements)

Scope is 2023–2025 tax years. Extend `_SLOTS` when adding a new year.
"""

from __future__ import annotations

from compliance_os.case_templates.schema import Slot, Template


_SECTIONS = {
    "0": "Case Summary",
    "1": "Entity",
    "2": "Tax Returns",
    "3": "Income Documents",
    "4": "Tax Compliance Issues",
    "5": "Ledger Records",
    "6": "Bank Statements",
}


_SLOTS: list[Slot] = [
    # ─── 0: Case Summary ─────────────────────────────────────────
    Slot(
        id="00_case_summary", section="0", section_name="Case Summary",
        title="Case summary narrative",
        description="Engagement brief: client, entity, issue, reportable transactions, open questions.",
        doc_types=["case_summary"],
        keywords=["case summary", "case_summary"],
        filename_patterns=[r"^00[_-].*(summary|brief|memo)", r"case[_\s-]?summary"],
    ),

    # ─── 1: Entity (BSGC LLC) ────────────────────────────────────
    Slot(
        id="01_articles_ss4", section="1", section_name="Entity",
        title="Articles of Organization + SS-4",
        description="Formation filing + EIN application.",
        doc_types=["articles", "ss4"],
        keywords=["articles", "ss-4", "ss4"],
        filename_patterns=[r"articles.*ss[-_]?4", r"ss[-_]?4.*articles", r"articles_and_ss4"],
    ),
    Slot(
        id="01_ein_notice", section="1", section_name="Entity",
        title="EIN notice",
        description="IRS CP-575 or equivalent EIN confirmation.",
        doc_types=["ein_notice"],
        keywords=["ein", "cp575", "cp-575", "ein notice"],
        filename_patterns=[r"ein[_\s-]?notice", r"cp[-_]?575"],
    ),
    Slot(
        id="01_formation", section="1", section_name="Entity",
        title="State formation filing",
        description="State-of-formation certificate / filing evidence.",
        doc_types=["formation"],
        keywords=["formation", "wyoming", "state filing"],
        filename_patterns=[r"formation", r"wyoming"],
    ),
    Slot(
        id="01_operating_agreement", section="1", section_name="Entity",
        title="Operating agreement",
        description="LLC operating agreement.",
        doc_types=["operating_agreement"],
        keywords=["operating agreement", "operating_agreement"],
        filename_patterns=[r"operating[_\s-]?agreement"],
    ),

    # ─── 2: Tax Returns (by year) ────────────────────────────────
    Slot(
        id="02_2023_return", section="2", section_name="Tax Returns",
        title="2023 tax return",
        description="Filed 2023 return (1040 or 1040-NR; being amended).",
        doc_types=["tax_return"],
        keywords=["2023", "taxreturn", "tax return", "1040"],
        filename_patterns=[r"2023[_\s-]?tax", r"tax.*2023", r"2023.*return"],
    ),
    Slot(
        id="02_2024_return", section="2", section_name="Tax Returns",
        title="2024 tax return",
        description="Filed 2024 return (1040, being amended to 1040-NR).",
        doc_types=["tax_return"],
        keywords=["2024", "taxreturn", "tax return", "1040"],
        filename_patterns=[r"2024[_\s-]?tax", r"tax.*2024", r"2024.*return"],
    ),
    Slot(
        id="02_2025_return", section="2", section_name="Tax Returns",
        title="2025 tax return",
        description="2025 return (to be prepared).",
        required=False,
        doc_types=["tax_return"],
        keywords=["2025", "taxreturn", "tax return", "1040"],
        filename_patterns=[r"2025[_\s-]?tax", r"tax.*2025", r"2025.*return"],
    ),

    # ─── 3: Income Documents ─────────────────────────────────────
    # 2023
    Slot(
        id="03_2023_w2_vcv", section="3", section_name="Income Documents",
        title="2023 W-2 — VCV",
        doc_types=["w2"],
        keywords=["2023", "w2", "w-2", "vcv"],
        filename_patterns=[r"2023.*w[-_]?2.*vcv", r"w[-_]?2.*vcv.*2023"],
    ),
    Slot(
        id="03_2023_1042s_tda", section="3", section_name="Income Documents",
        title="2023 1042-S — TD Ameritrade",
        doc_types=["1042s"],
        keywords=["2023", "1042s", "1042-s", "tda", "ameritrade"],
        filename_patterns=[r"2023.*1042[-_]?s.*tda", r"1042[-_]?s.*tda.*2023"],
    ),

    # 2024
    Slot(
        id="03_2024_w2_vcv", section="3", section_name="Income Documents",
        title="2024 W-2 — VCV",
        doc_types=["w2"],
        keywords=["2024", "w2", "w-2", "vcv"],
        filename_patterns=[r"2024.*w[-_]?2.*vcv"],
    ),
    Slot(
        id="03_2024_w2_bitsync", section="3", section_name="Income Documents",
        title="2024 W-2 — BitSync",
        doc_types=["w2"],
        keywords=["2024", "w2", "w-2", "bitsync"],
        filename_patterns=[r"2024.*w[-_]?2.*bitsync"],
    ),
    Slot(
        id="03_2024_1042s_tda", section="3", section_name="Income Documents",
        title="2024 1042-S — TD Ameritrade",
        doc_types=["1042s"],
        keywords=["2024", "1042s", "1042-s", "tda"],
        filename_patterns=[r"2024.*1042[-_]?s.*tda(?!.*updated)"],
    ),
    Slot(
        id="03_2024_1042s_tda_updated", section="3", section_name="Income Documents",
        title="2024 1042-S — TD Ameritrade (corrected)",
        required=False,
        doc_types=["1042s"],
        keywords=["2024", "1042s", "1042-s", "tda", "updated", "corrected"],
        filename_patterns=[r"2024.*1042[-_]?s.*tda.*updated", r"tda.*updated"],
    ),
    Slot(
        id="03_2024_1042s_schwab", section="3", section_name="Income Documents",
        title="2024 1042-S — Schwab",
        doc_types=["1042s"],
        keywords=["2024", "1042s", "1042-s", "schwab"],
        filename_patterns=[r"2024.*1042[-_]?s.*schwab"],
    ),
    Slot(
        id="03_2024_1099b_schwab", section="3", section_name="Income Documents",
        title="2024 1099-B — Schwab",
        description="May be split across multiple part files.",
        doc_types=["1099b"],
        keywords=["2024", "1099b", "1099-b", "schwab"],
        filename_patterns=[r"2024.*1099[-_]?b.*schwab"],
    ),
    Slot(
        id="03_2024_1099int_citibank", section="3", section_name="Income Documents",
        title="2024 1099-INT — Citibank LLC",
        doc_types=["1099int"],
        keywords=["2024", "1099int", "1099-int", "citibank"],
        filename_patterns=[r"2024.*1099[-_]?int.*citi"],
    ),
    Slot(
        id="03_2024_yearend_schwab", section="3", section_name="Income Documents",
        title="2024 year-end summary — Schwab",
        required=False,
        doc_types=["yearend_summary"],
        keywords=["2024", "year-end", "yearend", "schwab"],
        filename_patterns=[r"2024.*year[-_]?end.*schwab"],
    ),

    # 2025
    Slot(
        id="03_2025_w2_claudius", section="3", section_name="Income Documents",
        title="2025 W-2 — Claudius",
        doc_types=["w2"],
        keywords=["2025", "w2", "w-2", "claudius"],
        filename_patterns=[r"2025.*w[-_]?2.*claudius"],
    ),
    Slot(
        id="03_2025_w2_wolffli", section="3", section_name="Income Documents",
        title="2025 W-2 — Wolff & Li",
        doc_types=["w2"],
        keywords=["2025", "w2", "w-2", "wolffli", "wolff"],
        filename_patterns=[r"2025.*w[-_]?2.*wolff"],
    ),
    Slot(
        id="03_2025_1042s_schwab", section="3", section_name="Income Documents",
        title="2025 1042-S — Schwab",
        doc_types=["1042s"],
        keywords=["2025", "1042s", "1042-s", "schwab"],
        filename_patterns=[r"2025.*1042[-_]?s.*schwab"],
    ),
    Slot(
        id="03_2025_1098t_ciam", section="3", section_name="Income Documents",
        title="2025 1098-T — CIAM",
        required=False,
        doc_types=["1098t"],
        keywords=["2025", "1098t", "1098-t", "ciam"],
        filename_patterns=[r"2025.*1098[-_]?t.*ciam"],
    ),

    # ─── 4: Tax Compliance Issues ────────────────────────────────
    Slot(
        id="04_issues_memo", section="4", section_name="Tax Compliance Issues",
        title="Tax compliance issues register",
        description="Comprehensive analysis of flagged items for CPA attention.",
        doc_types=["issues_memo"],
        keywords=["compliance", "issues", "issues memo", "compliance_issues"],
        filename_patterns=[r"^04[_-]", r"(tax[_\s-]?)?compliance.*issues", r"issues[_\s-]?memo"],
    ),

    # ─── 5: Ledger Records ───────────────────────────────────────
    Slot(
        id="05_capital_ledger", section="5", section_name="Ledger Records",
        title="Capital account ledger",
        description="Reportable capital contributions + distributions.",
        doc_types=["capital_ledger"],
        keywords=["capital", "ledger", "capital account"],
        filename_patterns=[r"capital[_\s-]?account", r"capital[_\s-]?ledger"],
    ),
    Slot(
        id="05_facts_sheet", section="5", section_name="Ledger Records",
        title="LLC facts sheet",
        required=False,
        doc_types=["facts_sheet"],
        keywords=["facts sheet", "facts_sheet"],
        filename_patterns=[r"facts[_\s-]?sheet"],
    ),

    # ─── 6: Bank / Brokerage Statements ──────────────────────────
    Slot(
        id="06_citibank_transactions", section="6", section_name="Bank Statements",
        title="Citibank LLC transactions (CSV)",
        doc_types=["bank_transactions"],
        keywords=["citibank", "transactions"],
        filename_patterns=[r"citibank.*transactions", r"citi.*llc.*transactions"],
    ),
    Slot(
        id="06_schwab_transactions", section="6", section_name="Bank Statements",
        title="Schwab LLC transactions (CSV)",
        doc_types=["brokerage_transactions"],
        keywords=["schwab", "transactions"],
        filename_patterns=[r"schwab.*llc.*transactions", r"schwab.*transactions"],
    ),
    Slot(
        id="06_schwab_account_summary", section="6", section_name="Bank Statements",
        title="Schwab LLC 2025 account summary",
        required=False,
        doc_types=["account_summary"],
        keywords=["schwab", "account summary", "account_summary"],
        filename_patterns=[r"schwab.*llc.*2025.*summary", r"schwab.*account[_\s-]?summary"],
    ),
]


CPA_TEMPLATE = Template(
    id="cpa_nr_entity",
    name="CPA Tax Engagement Package",
    description=(
        "Complete document set for a nonresident alien tax engagement "
        "involving a foreign-owned domestic disregarded entity "
        "(Form 5472 + pro forma 1120). Covers case summary, entity "
        "formation, tax returns by year, income documents, compliance "
        "issues register, LLC ledger, and bank/brokerage statements."
    ),
    sections=_SECTIONS,
    slots=_SLOTS,
)
