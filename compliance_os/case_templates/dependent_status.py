"""Dependent status (F-2 / J-2 / H-4) case template (generic, no PII)."""

from compliance_os.case_templates.schema import Slot, Template

_SECTIONS = {
    "A": "Principal Linkage",
    "B": "Dependent Identity",
    "C": "Relationship Evidence",
    "D": "Status Documents",
}

_SLOTS = [
    Slot(id="A1", section="A", section_name="Principal Linkage", title="Principal's status document",
         description="The principal visa holder's I-797 / I-20 / DS-2019 plus most recent I-94.",
         doc_types=["i797", "i20", "ds2019", "i94"], keywords=["i797", "i-20", "ds-2019", "i-94", "principal"],
         filename_patterns=[r"(i[-_]?797|i[-_]?20|ds[-_]?2019|i[-_]?94)", r"^A1[_-]"]),
    Slot(id="A2", section="A", section_name="Principal Linkage", title="Principal's visa stamp",
         description="Principal's visa stamp.", required=False,
         keywords=["visa", "stamp"], filename_patterns=[r"visa", r"^A2[_-]"]),
    Slot(id="B1", section="B", section_name="Dependent Identity", title="Dependent passport bio page",
         description="Dependent's passport biographic page.",
         doc_types=["passport"], keywords=["passport", "dependent"], filename_patterns=[r"passport", r"^B1[_-]"]),
    Slot(id="B2", section="B", section_name="Dependent Identity", title="Dependent I-94",
         description="Dependent's most recent I-94.",
         doc_types=["i94"], keywords=["i-94", "i94"], filename_patterns=[r"i[-_]?94", r"^B2[_-]"]),
    Slot(id="C1", section="C", section_name="Relationship Evidence", title="Marriage certificate (spouse)",
         description="Marriage certificate for a dependent spouse.", required=False,
         keywords=["marriage", "certificate"], filename_patterns=[r"marriage", r"^C1[_-]"]),
    Slot(id="C2", section="C", section_name="Relationship Evidence", title="Birth certificate (child)",
         description="Birth certificate for a dependent child.", required=False,
         keywords=["birth", "certificate"], filename_patterns=[r"birth", r"^C2[_-]"]),
    Slot(id="D1", section="D", section_name="Status Documents", title="Dependent status document",
         description="Dependent's I-20 (F-2) or DS-2019 (J-2).",
         doc_types=["i20", "ds2019"], keywords=["i-20", "ds-2019", "f-2", "j-2"],
         filename_patterns=[r"(i[-_]?20|ds[-_]?2019)", r"^D1[_-]"]),
    Slot(id="D2", section="D", section_name="Status Documents", title="Dependent EAD (H-4 if applicable)",
         description="Dependent's EAD card (H-4 work authorization, if applicable).", required=False,
         doc_types=["ead"], keywords=["ead", "h-4", "h4"], filename_patterns=[r"ead", r"^D2[_-]"]),
]

DEPENDENT_STATUS_TEMPLATE = Template(
    id="dependent_status",
    name="Dependent Status (F-2 / J-2 / H-4)",
    description="Generic document set for a dependent (F-2 / J-2 / H-4) spouse or child.",
    sections=_SECTIONS,
    slots=_SLOTS,
)
