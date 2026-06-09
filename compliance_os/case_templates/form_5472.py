"""Form 5472 (foreign-owned single-member LLC) case template (generic, no PII)."""

from compliance_os.case_templates.schema import Slot, Template

_SECTIONS = {
    "0": "Summary",
    "1": "Entity & EIN",
    "2": "Foreign Owner",
    "3": "Reportable Transactions",
    "4": "Filing",
}

_SLOTS = [
    Slot(id="S0", section="0", section_name="Summary", title="Engagement summary",
         description="One-page summary of the foreign-owned disregarded-entity situation.",
         required=False, keywords=["summary", "engagement"], filename_patterns=[r"summary", r"^S0[_-]"]),
    Slot(id="E1", section="1", section_name="Entity & EIN", title="EIN assignment letter (CP-575)",
         description="IRS CP-575 (or 147C) showing the LLC's EIN.",
         doc_types=["ein_letter"], keywords=["cp-575", "cp575", "ein"],
         filename_patterns=[r"cp[-_ ]?575", r"ein", r"^E1[_-]"]),
    Slot(id="E2", section="1", section_name="Entity & EIN", title="Certificate of Formation",
         description="State Certificate of Formation / Articles of Organization.",
         keywords=["formation", "articles", "certificate"],
         filename_patterns=[r"(formation|articles)", r"^E2[_-]"]),
    Slot(id="E3", section="1", section_name="Entity & EIN", title="Operating agreement",
         description="LLC operating agreement.", required=False,
         keywords=["operating agreement"], filename_patterns=[r"operating[_ -]?agreement", r"^E3[_-]"]),
    Slot(id="O1", section="2", section_name="Foreign Owner", title="Foreign owner ID",
         description="Foreign owner's passport / national ID establishing non-US-person status.",
         doc_types=["passport"], keywords=["passport", "owner", "foreign"],
         filename_patterns=[r"passport", r"owner", r"^O1[_-]"]),
    Slot(id="T1", section="3", section_name="Reportable Transactions", title="Reportable-transaction ledger",
         description="Ledger of reportable transactions (capital contributions, distributions, loans) between the LLC and its foreign owner — the content of Form 5472 Parts IV/V.",
         keywords=["ledger", "transactions", "capital", "contribution"],
         filename_patterns=[r"(ledger|transaction|capital)", r"^T1[_-]"]),
    Slot(id="T2", section="3", section_name="Reportable Transactions", title="Pro-forma 1120 cover",
         description="Pro-forma Form 1120 that accompanies Form 5472.", required=False,
         keywords=["1120", "pro forma", "proforma"], filename_patterns=[r"1120", r"^T2[_-]"]),
    Slot(id="F1", section="4", section_name="Filing", title="Form 5472 draft / filed copy",
         description="Draft or filed Form 5472.", required=False,
         keywords=["5472"], filename_patterns=[r"5472", r"^F1[_-]"]),
]

FORM_5472_TEMPLATE = Template(
    id="form_5472_dre",
    name="Form 5472 — Foreign-Owned Single-Member LLC",
    description="Generic document set for a foreign-owned single-member (disregarded-entity) US LLC that must file Form 5472 + a pro-forma 1120.",
    sections=_SECTIONS,
    slots=_SLOTS,
)
