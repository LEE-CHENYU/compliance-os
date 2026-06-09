"""Founder / owner-beneficiary H-1B petition case template (generic, no PII)."""

from compliance_os.case_templates.schema import Slot, Template

_SECTIONS = {
    "A": "Beneficiary",
    "B": "E-Verify Enrollment",
    "C": "Ownership & Cap Table",
    "D": "Corporate Governance",
    "E": "Employer-Employee Relationship",
    "F": "H-1B Registration",
}

_SLOTS = [
    Slot(id="A1", section="A", section_name="Beneficiary", title="Passport bio page + I-94",
         description="Beneficiary passport biographic page and most recent I-94.",
         doc_types=["passport", "i94"], keywords=["passport", "i-94", "i94"],
         filename_patterns=[r"passport", r"i[-_]?94", r"^A1[_-]"]),
    Slot(id="A2", section="A", section_name="Beneficiary", title="Qualifying degree + transcript",
         description="Degree diploma and transcript establishing the specialty-occupation qualification.",
         doc_types=["transcript"], keywords=["degree", "diploma", "transcript"],
         filename_patterns=[r"(degree|diploma|transcript)", r"^A2[_-]"]),
    Slot(id="A3", section="A", section_name="Beneficiary", title="Current immigration status document",
         description="Current EAD / I-20 / I-797 showing present status (e.g. STEM OPT).",
         required=False, doc_types=["ead", "i20", "i797"], keywords=["ead", "i-20", "i797", "status"],
         filename_patterns=[r"(ead|i[-_]?20|i[-_]?797)", r"^A3[_-]"]),
    Slot(id="B1", section="B", section_name="E-Verify Enrollment", title="E-Verify enrollment confirmation",
         description="Company E-Verify Memorandum of Understanding / enrollment confirmation (required for an owner-beneficiary employer).",
         doc_types=["e_verify_case"], keywords=["e-verify", "everify", "mou", "enrollment"],
         filename_patterns=[r"e[-_]?verify", r"mou", r"^B1[_-]"]),
    Slot(id="C1", section="C", section_name="Ownership & Cap Table", title="Cap table / controlling interest",
         description="Cap table showing the beneficiary's ownership percentage (controlling interest).",
         keywords=["cap table", "ownership", "equity", "shareholder"],
         filename_patterns=[r"cap[_ -]?table", r"ownership", r"^C1[_-]"]),
    Slot(id="C2", section="C", section_name="Ownership & Cap Table", title="Stock certificates / membership units",
         description="Evidence of issued shares or LLC membership units to the beneficiary.",
         required=False, keywords=["stock certificate", "membership", "units", "shares"],
         filename_patterns=[r"(stock|share|membership)", r"^C2[_-]"]),
    Slot(id="D1", section="D", section_name="Corporate Governance", title="Bylaws / operating agreement",
         description="Corporate bylaws or LLC operating agreement with hire/fire/supervise provisions.",
         keywords=["bylaws", "operating agreement", "governance"],
         filename_patterns=[r"(bylaws|operating[_ -]?agreement)", r"^D1[_-]"]),
    Slot(id="D2", section="D", section_name="Corporate Governance", title="Board resolution — independent oversight",
         description="Board/manager resolution establishing an independent body that can hire, fire, and supervise the founder-beneficiary (bona-fide employer-employee relationship).",
         keywords=["board resolution", "resolution", "minutes", "oversight"],
         filename_patterns=[r"(board|resolution|minutes)", r"^D2[_-]"]),
    Slot(id="E1", section="E", section_name="Employer-Employee Relationship", title="Right-to-control evidence",
         description="Documentation that the company (not the beneficiary alone) controls the beneficiary's employment — e.g. a board resolution authorizing hire/fire of the founder.",
         keywords=["employment agreement", "offer letter", "control", "hire"],
         filename_patterns=[r"(employment|offer|control)", r"^E1[_-]"]),
    Slot(id="F1", section="F", section_name="H-1B Registration", title="H-1B registration selection + G-28",
         description="H-1B registration selection notice and G-28 (if represented by counsel).",
         doc_types=["h1b_g28"], keywords=["registration", "selection", "g-28", "g28"],
         filename_patterns=[r"(registration|selection|g[-_]?28)", r"^F1[_-]"]),
]

FOUNDER_H1B_TEMPLATE = Template(
    id="founder_h1b_petition",
    name="Founder / Owner-Beneficiary H-1B Petition",
    description="Generic document set for a founder self-sponsoring an H-1B as the owner-beneficiary of their own company (E-Verify enrollment, controlling interest, and a bona-fide employer-employee relationship).",
    sections=_SECTIONS,
    slots=_SLOTS,
)
