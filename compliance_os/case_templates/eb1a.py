"""EB-1A extraordinary-ability evidence case template (generic, no PII)."""

from compliance_os.case_templates.schema import Slot, Template

_SECTIONS = {
    "0": "Petition Core",
    "1": "Awards",
    "2": "Memberships",
    "3": "Published Material About",
    "4": "Judging",
    "5": "Original Contributions",
    "6": "Scholarly Articles",
    "7": "High Remuneration",
}

_SLOTS = [
    Slot(id="P1", section="0", section_name="Petition Core", title="Form I-140 + petition letter",
         description="Form I-140 and the cover/petition letter.",
         keywords=["i-140", "i140", "petition"], filename_patterns=[r"i[-_]?140", r"petition", r"^P1[_-]"]),
    Slot(id="P2", section="0", section_name="Petition Core", title="CV / evidence index",
         description="Beneficiary CV and an index of the evidence.",
         keywords=["cv", "resume", "index"], filename_patterns=[r"(cv|resume|index)", r"^P2[_-]"]),
    Slot(id="C1", section="1", section_name="Awards", title="Nationally/internationally recognized awards",
         description="Evidence of recognized awards for excellence (8 CFR 204.5(h)(3)(i)).",
         required=False, keywords=["award", "prize", "medal"], filename_patterns=[r"(award|prize)", r"^C1[_-]"]),
    Slot(id="C2", section="2", section_name="Memberships", title="Memberships requiring outstanding achievement",
         description="Evidence of memberships requiring outstanding achievement (criterion ii).",
         required=False, keywords=["membership", "fellow", "association"], filename_patterns=[r"(membership|fellow)", r"^C2[_-]"]),
    Slot(id="C3", section="3", section_name="Published Material About", title="Published material about the beneficiary",
         description="Articles/media about the beneficiary and their work (criterion iii).",
         required=False, keywords=["press", "article", "media", "published"], filename_patterns=[r"(press|article|media)", r"^C3[_-]"]),
    Slot(id="C4", section="4", section_name="Judging", title="Evidence of judging others' work",
         description="Evidence the beneficiary judged the work of others (criterion iv).",
         required=False, keywords=["reviewer", "judge", "panel"], filename_patterns=[r"(review|judg|panel)", r"^C4[_-]"]),
    Slot(id="C5", section="5", section_name="Original Contributions", title="Original contributions of major significance",
         description="Evidence of original contributions of major significance (criterion v).",
         required=False, keywords=["contribution", "patent", "citation"], filename_patterns=[r"(contribution|patent|citation)", r"^C5[_-]"]),
    Slot(id="C6", section="6", section_name="Scholarly Articles", title="Authorship of scholarly articles",
         description="Beneficiary's authored scholarly articles (criterion vi).",
         required=False, keywords=["publication", "scholarly", "journal", "paper"], filename_patterns=[r"(publication|journal|paper)", r"^C6[_-]"]),
    Slot(id="C8", section="7", section_name="High Remuneration", title="High salary / remuneration evidence",
         description="Evidence of high salary or remuneration relative to the field (criterion viii).",
         required=False, keywords=["salary", "compensation", "remuneration"], filename_patterns=[r"(salary|compensation|remuneration)", r"^C8[_-]"]),
]

EB1A_TEMPLATE = Template(
    id="eb1a_evidence",
    name="EB-1A Extraordinary Ability Evidence",
    description="Generic evidence buckets for an EB-1A self-petition, organized by the 8 CFR 204.5(h)(3) regulatory criteria (satisfy at least 3 of 8).",
    sections=_SECTIONS,
    slots=_SLOTS,
)
