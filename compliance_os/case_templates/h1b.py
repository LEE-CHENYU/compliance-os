"""H-1B petition case template.

Derived from a standard H-1B petition package structure. Covers the full
F-1 → OPT → STEM OPT → CPT → H-1B lineage plus petitioner corporate
formation, registration, and business plan evidence.

Section layout:
  A — Beneficiary (passport, I-94, degrees, EADs, transcripts, CV)
  B — I-20 History (chronological, by school/transfer)
  C — CPT Academic Evidence
  D — Corporate (petitioner entity formation, governance, finance)
  E — H-1B Registration (FY lottery selection, G-28s)
  F — Employment History (SEVIS record, I-983s, terminations)
  G — Business Plans
"""

from __future__ import annotations

from compliance_os.case_templates.schema import Slot, Template


_SECTIONS = {
    "A": "Beneficiary",
    "B": "I-20 History",
    "C": "CPT Academic Evidence",
    "D": "Corporate (Petitioner)",
    "E": "H-1B Registration",
    "F": "Employment History",
    "G": "Business Plans",
}


_SLOTS: list[Slot] = [
    # ─── A: Beneficiary ──────────────────────────────────────────
    Slot(
        id="A1", section="A", section_name="Beneficiary",
        title="Passport bio page",
        description="Current passport biographic page with photo and expiry.",
        doc_types=["passport"],
        keywords=["passport", "bio", "biographic"],
        filename_patterns=[r"passport", r"bio.*page", r"^A1[_-]"],
    ),
    Slot(
        id="A2", section="A", section_name="Beneficiary",
        title="I-94 most recent",
        description="Most recent admission record from CBP.",
        doc_types=["i94"],
        keywords=["i-94", "i94", "admission"],
        filename_patterns=[r"i[-_]?94", r"^A2[_-]"],
    ),
    Slot(
        id="A3", section="A", section_name="Beneficiary",
        title="Graduate degree diploma",
        description="Master's qualifying-degree diploma.",
        doc_types=["diploma", "degree"],
        keywords=["degree", "diploma", "master", "ms"],
        filename_patterns=[r"(degree|diploma)", r"^A3[_-]"],
    ),
    Slot(
        id="A4", section="A", section_name="Beneficiary",
        title="Graduate transcript",
        description="Official graduate-level transcript.",
        doc_types=["transcript"],
        keywords=["transcript", "graduate"],
        filename_patterns=[r"transcript", r"^A4[_-]"],
    ),
    Slot(
        id="A5", section="A", section_name="Beneficiary",
        title="CV / resume",
        description="H-1B-tailored CV.",
        doc_types=["cv", "resume"],
        keywords=["cv", "resume", "curriculum vitae"],
        filename_patterns=[r"\bcv\b", r"resume", r"^A5[_-]"],
    ),
    Slot(
        id="A6", section="A", section_name="Beneficiary",
        title="F-1 visa stamp page",
        description="Current F-1 visa stamp in passport.",
        doc_types=["visa"],
        keywords=["f-1", "f1", "visa", "stamp"],
        filename_patterns=[r"visa.*(stamp|f[-_]?1)", r"f[-_]?1.*visa", r"^A6[_-]"],
    ),
    Slot(
        id="A7", section="A", section_name="Beneficiary",
        title="OPT EAD card",
        description="Post-completion OPT EAD card.",
        doc_types=["ead"],
        keywords=["ead", "opt"],
        filename_patterns=[r"ead.*opt(?!.*stem)", r"opt.*ead(?!.*stem)", r"^A7[_-]"],
    ),
    Slot(
        id="A8", section="A", section_name="Beneficiary",
        title="STEM OPT EAD card",
        description="STEM OPT EAD card.",
        doc_types=["ead"],
        keywords=["ead", "stem", "stemopt", "stem opt"],
        filename_patterns=[r"stem.*ead", r"ead.*stem", r"^A8[_-]"],
    ),
    Slot(
        id="A9", section="A", section_name="Beneficiary",
        title="Current school enrollment letter",
        description="Proof of current enrollment at current school.",
        required=False,
        doc_types=["enrollment_letter"],
        keywords=["enrollment"],
        filename_patterns=[r"enroll", r"^A9[_-]"],
    ),
    Slot(
        id="A10", section="A", section_name="Beneficiary",
        title="Bachelor's transcript",
        description="Undergraduate transcript.",
        required=False,
        doc_types=["transcript"],
        keywords=["bachelor", "undergraduate", "transcript"],
        filename_patterns=[r"(bachelor|undergrad).*transcript", r"^A10[_-]"],
    ),
    Slot(
        id="A11", section="A", section_name="Beneficiary",
        title="Exchange/study-abroad transcript",
        description="Exchange or study-abroad program transcript.",
        required=False,
        doc_types=["transcript"],
        keywords=["exchange", "study abroad", "transcript"],
        filename_patterns=[r"exchange.*transcript", r"^A11[_-]"],
    ),

    # ─── B: I-20 History (chronological) ──────────────────────────
    *[
        Slot(
            id=f"B{n:02d}", section="B", section_name="I-20 History",
            title=title, description=desc,
            doc_types=["i20"],
            keywords=["i-20", "i20"] + kw,
            filename_patterns=[rf"^B{n:02d}[_-]", rf"i[-_]?20.*{pat}" if pat else r"i[-_]?20"],
            order=n, phase=phase,
        )
        for n, title, desc, kw, pat, phase in [
            (1, "I-20 initial issuance",              "Initial school I-20 issuance.",              ["initial", "original"],           "initial|orig",             "school1"),
            (2, "I-20 travel signature (first)",      "Travel signature, first instance.",           ["travel"],                        "travel",                   "school1"),
            (3, "I-20 travel signature (second)",     "Travel signature, second instance.",          ["travel"],                        "travel",                   "school1"),
            (4, "I-20 OPT endorsement",               "OPT endorsement.",                            ["opt"],                           "opt",                      "opt"),
            (5, "I-20 STEM OPT endorsement",          "STEM OPT endorsement.",                       ["stem"],                          "stem",                     "stem_opt"),
            (6, "I-20 STEM OPT endorsement (signed)", "Signed/updated STEM OPT version.",            ["stem", "signed"],                "stem.*sign",               "stem_opt"),
            (7, "I-20 transfer to new school (pending)","Transfer to new school pending.",           ["transfer"],                      "transfer",                 "new_school"),
            (8, "I-20 new school continuation",       "New school continuation.",                    ["continued"],                     "continu",                  "new_school"),
            (9, "I-20 transfer to current school",    "Transfer to current school.",                 ["transfer", "current"],           "transfer.*current|current.*transfer", "current"),
            (10,"I-20 CPT endorsement (employer A)",  "CPT endorsement for employer A.",             ["cpt"],                           "cpt",                      "cpt_employer_a"),
            (11,"I-20 current school",                "Most recent current-school I-20.",            ["current"],                       "current",                  "current"),
            (12,"I-20 CPT endorsement (employer B)",  "CPT endorsement for employer B.",             ["cpt"],                           "cpt",                      "cpt_employer_b"),
        ]
    ],
    # B13 is forward-looking (not yet issued at filing time); optional
    Slot(
        id="B13", section="B", section_name="I-20 History",
        title="I-20 CPT (forward-looking) to bridge a status gap (if applicable)",
        description="Forward-looking CPT I-20 needed to bridge a status gap, if applicable.",
        required=False,
        doc_types=["i20"],
        keywords=["i-20", "i20", "cpt", "forward"],
        filename_patterns=[r"^B13[_-]", r"cpt.*forward", r"forward.*cpt"],
        order=13, phase="cpt_forward",
    ),

    # ─── C: CPT Academic Evidence ─────────────────────────────────
    Slot(
        id="C1", section="C", section_name="CPT Academic Evidence",
        title="CPT academic evidence summary",
        description="Compiled exhibit: enrollments, grades, submissions.",
        doc_types=["academic_evidence"],
        keywords=["canvas", "cpt", "evidence", "academic"],
        filename_patterns=[r"canvas", r"academic.*evidence", r"cpt.*academic", r"^C1[_-]"],
    ),
    Slot(
        id="C2", section="C", section_name="CPT Academic Evidence",
        title="CPT training plan / application",
        description="CPT training plan form from DSO.",
        doc_types=["cpt_training_plan"],
        keywords=["cpt", "training plan", "application"],
        filename_patterns=[r"cpt.*(training|application)", r"^C2[_-]"],
    ),
    Slot(
        id="C3", section="C", section_name="CPT Academic Evidence",
        title="Internship course syllabus",
        description="Internship course syllabus demonstrating course integration.",
        required=False,
        doc_types=["syllabus"],
        keywords=["syllabus", "internship"],
        filename_patterns=[r"int\s*\d{3}", r"syllabus", r"^C3[_-]"],
    ),

    # ─── D: Corporate (Petitioner) ────────────────────────────────
    Slot(
        id="D1", section="D", section_name="Corporate (Petitioner)",
        title="Articles of Incorporation + SS-4",
        description="Formation docs + EIN application.",
        doc_types=["articles_incorporation"],
        keywords=["articles", "incorporation", "ss-4", "ss4"],
        filename_patterns=[r"articles.*incorp", r"ss[-_]?4", r"^D1[_-]"],
    ),
    Slot(
        id="D2", section="D", section_name="Corporate (Petitioner)",
        title="Bylaws",
        doc_types=["bylaws"],
        keywords=["bylaws"],
        filename_patterns=[r"bylaws", r"^D2[_-]"],
    ),
    Slot(
        id="D3", section="D", section_name="Corporate (Petitioner)",
        title="Corporate resolutions",
        doc_types=["corporate_resolution"],
        keywords=["corporate resolution", "resolutions"],
        filename_patterns=[r"corporate.*resolution", r"^D3[_-]"],
    ),
    Slot(
        id="D4", section="D", section_name="Corporate (Petitioner)",
        title="SOI + Good Standing",
        description="Statement of Information + certificate of good standing.",
        doc_types=["soi", "good_standing"],
        keywords=["soi", "statement of information", "good standing"],
        filename_patterns=[r"soi", r"good.*standing", r"^D4[_-]"],
    ),
    Slot(
        id="D5", section="D", section_name="Corporate (Petitioner)",
        title="Governance documents (signed)",
        doc_types=["governance"],
        keywords=["governance", "signed"],
        filename_patterns=[r"governance", r"^D5[_-]"],
    ),
    Slot(
        id="D6", section="D", section_name="Corporate (Petitioner)",
        title="Key documents compilation",
        required=False,
        doc_types=["corporate_compilation"],
        keywords=["key documents", "compilation"],
        filename_patterns=[r"key.*documents", r"compilation", r"^D6[_-]"],
    ),
    Slot(
        id="D7", section="D", section_name="Corporate (Petitioner)",
        title="EIN cancellation letter",
        description="Duplicate EIN cancellation.",
        required=False,
        doc_types=["ein_cancellation"],
        keywords=["ein", "cancel", "cancellation"],
        filename_patterns=[r"ein.*cancel", r"^D7[_-]"],
    ),
    Slot(
        id="D8", section="D", section_name="Corporate (Petitioner)",
        title="EIN fax notification",
        required=False,
        doc_types=["ein_notice"],
        keywords=["ein", "fax", "notification"],
        filename_patterns=[r"ein.*fax", r"^D8[_-]"],
    ),
    Slot(
        id="D9", section="D", section_name="Corporate (Petitioner)",
        title="Office lease",
        description="Commercial lease agreement (extract or full).",
        doc_types=["lease"],
        keywords=["lease", "office", "commercial", "sublease"],
        filename_patterns=[r"lease", r"^D9[_-]"],
    ),
    Slot(
        id="D10", section="D", section_name="Corporate (Petitioner)",
        title="FTB withholding notice",
        required=False,
        doc_types=["ftb_notice"],
        keywords=["ftb", "withholding"],
        filename_patterns=[r"ftb", r"withholding", r"^D10[_-]"],
    ),
    Slot(
        id="D11", section="D", section_name="Corporate (Petitioner)",
        title="Board resolution — signing authority",
        description="Establishes hire/fire authority (employer-employee).",
        doc_types=["board_resolution"],
        keywords=["board resolution", "signing authority", "hire", "fire"],
        filename_patterns=[r"board.*resolution", r"signing.*authority", r"^D11[_-]"],
    ),
    Slot(
        id="D12", section="D", section_name="Corporate (Petitioner)",
        title="EIN CP575 notice",
        doc_types=["ein_notice"],
        keywords=["cp575", "ein"],
        filename_patterns=[r"cp[-_]?575", r"^D12[_-]"],
    ),
    Slot(
        id="D13", section="D", section_name="Corporate (Petitioner)",
        title="Affidavit of financial support",
        required=False,
        doc_types=["affidavit"],
        keywords=["affidavit", "financial support"],
        filename_patterns=[r"affidavit.*financial", r"^D13[_-]"],
    ),
    Slot(
        id="D14", section="D", section_name="Corporate (Petitioner)",
        title="Corporate bank statement",
        description="Petitioner ability-to-pay evidence.",
        doc_types=["bank_statement"],
        keywords=["bank statement", "corporate"],
        filename_patterns=[r"bank.*statement", r"^D14[_-]"],
    ),
    Slot(
        id="D15", section="D", section_name="Corporate (Petitioner)",
        title="Full commercial lease",
        required=False,
        doc_types=["lease"],
        keywords=["lease", "commercial", "full"],
        filename_patterns=[r"lease.*full", r"full.*lease", r"^D15[_-]"],
    ),

    # ─── E: H-1B Registration ─────────────────────────────────────
    Slot(
        id="E1", section="E", section_name="H-1B Registration",
        title="FY selection notice",
        description="USCIS registration selection notice.",
        doc_types=["h1b_selection_notice"],
        keywords=["selection notice", "fy2027", "h-1b", "h1b", "lottery"],
        filename_patterns=[r"selection.*notice", r"fy\d{4}", r"^E1[_-]"],
    ),
    Slot(
        id="E2", section="E", section_name="H-1B Registration",
        title="G-28 (primary petitioner)",
        description="Notice of attorney representation for registration.",
        doc_types=["g28"],
        keywords=["g-28", "g28", "attorney"],
        filename_patterns=[r"g[-_]?28", r"^E2[_-]"],
    ),
    Slot(
        id="E3", section="E", section_name="H-1B Registration",
        title="Primary registration draft/confirmation",
        doc_types=["h1b_registration"],
        keywords=["registration", "draft", "confirmation"],
        filename_patterns=[r"registration.*(draft|confirm)", r"^E3[_-]"],
    ),
    Slot(
        id="E4", section="E", section_name="H-1B Registration",
        title="G-28 (secondary, if dual registered)",
        required=False,
        doc_types=["g28"],
        keywords=["g-28", "g28", "secondary"],
        filename_patterns=[r"g[-_]?28.*secondary", r"^E4[_-]"],
    ),
    Slot(
        id="E5", section="E", section_name="H-1B Registration",
        title="Secondary registration draft",
        required=False,
        doc_types=["h1b_registration"],
        keywords=["registration", "secondary"],
        filename_patterns=[r"registration.*secondary", r"^E5[_-]"],
    ),

    # ─── F: Employment History ────────────────────────────────────
    Slot(
        id="F1", section="F", section_name="Employment History",
        title="SEVIS employment record",
        description="Definitive SEVIS record of all employers.",
        doc_types=["sevis_record"],
        keywords=["sevis", "employment record"],
        filename_patterns=[r"sevis.*(record|employment)", r"^F1[_-]"],
    ),
    Slot(
        id="F2", section="F", section_name="Employment History",
        title="Prior employer termination letter",
        description="Termination letter establishing clean end date.",
        required=False,
        doc_types=["termination_letter"],
        keywords=["termination", "separation"],
        filename_patterns=[r"termination", r"separation.*letter", r"^F2[_-]"],
    ),
    Slot(
        id="F3", section="F", section_name="Employment History",
        title="Separate entity formation (if applicable)",
        description="Formation doc for unrelated entity (to establish non-relatedness).",
        required=False,
        doc_types=["llc_formation"],
        keywords=["formation", "llc", "entity"],
        filename_patterns=[r"formation", r"^F3[_-]"],
    ),
    Slot(
        id="F4a", section="F", section_name="Employment History",
        title="I-983 — STEM OPT employer #1",
        description="Signed I-983 training plan.",
        required=False,
        doc_types=["i983"],
        keywords=["i-983", "i983"],
        filename_patterns=[r"i[-_]?983", r"^F4a[_-]"],
    ),
    Slot(
        id="F4b", section="F", section_name="Employment History",
        title="I-983 — STEM OPT employer #2",
        required=False,
        doc_types=["i983"],
        keywords=["i-983", "i983"],
        filename_patterns=[r"i[-_]?983", r"^F4b[_-]"],
    ),
    Slot(
        id="F4c", section="F", section_name="Employment History",
        title="I-983 — STEM OPT employer #3",
        required=False,
        doc_types=["i983"],
        keywords=["i-983", "i983"],
        filename_patterns=[r"i[-_]?983", r"^F4c[_-]"],
    ),
    Slot(
        id="F4d", section="F", section_name="Employment History",
        title="I-983 — STEM OPT employer #4",
        required=False,
        doc_types=["i983"],
        keywords=["i-983", "i983"],
        filename_patterns=[r"i[-_]?983", r"^F4d[_-]"],
    ),
    Slot(
        id="F5a", section="F", section_name="Employment History",
        title="Unauthorized employer evidence — refusal",
        description="Evidence that employer refused to sign I-983.",
        required=False,
        doc_types=["correspondence"],
        keywords=["refused", "i-983", "i983"],
        filename_patterns=[r"refused.*i[-_]?983", r"^F5a[_-]"],
    ),
    Slot(
        id="F5b", section="F", section_name="Employment History",
        title="Unauthorized employer evidence — offer",
        required=False,
        doc_types=["offer_letter"],
        keywords=["offer letter", "offer"],
        filename_patterns=[r"offer.*letter", r"^F5b[_-]"],
    ),

    # ─── G: Business Plans ────────────────────────────────────────
    Slot(
        id="G1", section="G", section_name="Business Plans",
        title="Petitioner business plan",
        description="Current business plan for petitioning entity.",
        doc_types=["business_plan"],
        keywords=["business plan"],
        filename_patterns=[r"business.*plan", r"^G1[_-]"],
    ),
    Slot(
        id="G2", section="G", section_name="Business Plans",
        title="Product/division business plan",
        description="Secondary plan (e.g. flagship product) reinforcing going concern.",
        required=False,
        doc_types=["business_plan"],
        keywords=["business plan", "product"],
        filename_patterns=[r"product.*business.*plan", r"^G2[_-]"],
    ),
    Slot(
        id="G3", section="G", section_name="Business Plans",
        title="Integrated business plan v2",
        description="Updated plan incorporating attorney feedback.",
        required=False,
        doc_types=["business_plan"],
        keywords=["business plan", "v2", "integrated"],
        filename_patterns=[r"business.*plan.*v2", r"v2.*business.*plan", r"^G3[_-]"],
    ),
]


H1B_TEMPLATE = Template(
    id="h1b_petition",
    name="H-1B Petition Package",
    description=(
        "Complete document set for an H-1B petition filing. Includes "
        "beneficiary identity, full F-1/OPT/STEM OPT/CPT lineage, "
        "petitioner corporate formation, registration, employment "
        "history, and business plans."
    ),
    sections=_SECTIONS,
    slots=_SLOTS,
)
