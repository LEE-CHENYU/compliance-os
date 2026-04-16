"""H-1B petition case template.

Derived from the Klasko upload_041626 package structure. Covers the full
F-1 → OPT → STEM OPT → CPT → H-1B lineage plus petitioner corporate
formation, registration, and business plan evidence.

Section layout:
  A — Beneficiary (passport, I-94, degrees, EADs, transcripts, CV)
  B — I-20 History (chronological, Columbia → Westcliff → CIAM)
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
        title="Columbia MS degree",
        description="Columbia University MS Applied Analytics diploma.",
        doc_types=["diploma", "degree"],
        keywords=["columbia", "degree", "diploma", "master"],
        filename_patterns=[r"columbia.*(degree|diploma)", r"^A3[_-]"],
    ),
    Slot(
        id="A4", section="A", section_name="Beneficiary",
        title="Columbia MS transcript",
        description="Official Columbia transcript.",
        doc_types=["transcript"],
        keywords=["columbia", "transcript"],
        filename_patterns=[r"columbia.*transcript", r"^A4[_-]"],
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
        description="Post-completion OPT EAD card (IOE9041477055).",
        doc_types=["ead"],
        keywords=["ead", "opt"],
        filename_patterns=[r"ead.*opt(?!.*stem)", r"opt.*ead(?!.*stem)", r"^A7[_-]"],
    ),
    Slot(
        id="A8", section="A", section_name="Beneficiary",
        title="STEM OPT EAD card",
        description="STEM OPT EAD card (IOE9733115480).",
        doc_types=["ead"],
        keywords=["ead", "stem", "stemopt", "stem opt"],
        filename_patterns=[r"stem.*ead", r"ead.*stem", r"^A8[_-]"],
    ),
    Slot(
        id="A9", section="A", section_name="Beneficiary",
        title="CIAM enrollment letter",
        description="Proof of current enrollment at CIAM.",
        required=False,
        doc_types=["enrollment_letter"],
        keywords=["ciam", "enrollment"],
        filename_patterns=[r"ciam.*enroll", r"enroll.*ciam", r"^A9[_-]"],
    ),
    Slot(
        id="A10", section="A", section_name="Beneficiary",
        title="SJTU bachelor's transcript",
        description="Shanghai Jiao Tong University undergraduate transcript.",
        required=False,
        doc_types=["transcript"],
        keywords=["sjtu", "shanghai jiao tong", "jiao tong"],
        filename_patterns=[r"sjtu", r"jiao[_ -]?tong", r"^A10[_-]"],
    ),
    Slot(
        id="A11", section="A", section_name="Beneficiary",
        title="Waseda exchange transcript",
        description="Waseda University exchange program transcript.",
        required=False,
        doc_types=["transcript"],
        keywords=["waseda"],
        filename_patterns=[r"waseda", r"^A11[_-]"],
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
            (1, "I-20 Columbia original",       "Initial Columbia issuance.",      ["columbia", "original"],        "columbia.*(orig|initial)", "columbia"),
            (2, "I-20 Columbia travel 2022",     "Travel signature 2022.",           ["columbia", "travel", "2022"],  "columbia.*travel.*2022",     "columbia"),
            (3, "I-20 Columbia travel 2023",     "Travel signature 2023.",           ["columbia", "travel", "2023"],  "columbia.*travel.*2023",     "columbia"),
            (4, "I-20 Columbia OPT Jan 2023",    "OPT endorsement.",                 ["columbia", "opt", "2023"],     "columbia.*opt",              "opt"),
            (5, "I-20 Columbia STEM OPT",        "STEM OPT endorsement.",            ["columbia", "stem", "2024"],    "columbia.*stem",             "stem_opt"),
            (6, "I-20 Columbia STEM OPT signed", "Signed/updated STEM OPT version.", ["columbia", "stem", "signed"],  "columbia.*stem.*sign",       "stem_opt"),
            (7, "I-20 Westcliff transfer pending","Westcliff transfer pending.",     ["westcliff", "transfer"],       "westcliff.*transfer",        "westcliff"),
            (8, "I-20 Westcliff continued",      "Westcliff continuation.",          ["westcliff", "continued"],      "westcliff.*continu",         "westcliff"),
            (9, "I-20 CIAM transfer Sep 2025",   "Transfer to CIAM.",                ["ciam", "transfer", "2025"],    "ciam.*transfer",             "ciam"),
            (10,"I-20 CIAM CPT Wolff & Li",      "CIAM CPT with Wolff & Li.",        ["ciam", "cpt", "wolff"],        "ciam.*cpt.*wolff",           "cpt_wolff"),
            (11,"I-20 CIAM current",             "Most recent CIAM I-20.",           ["ciam", "current"],             "ciam.*current",              "ciam"),
            (12,"I-20 CIAM CPT Yangtze",         "CPT endorsement for Yangtze.",     ["ciam", "cpt", "yangtze"],      "ciam.*cpt.*yangtze",         "cpt_yangtze"),
        ]
    ],
    # B13 is forward-looking (not yet issued at filing time); optional
    Slot(
        id="B13", section="B", section_name="I-20 History",
        title="I-20 CIAM CPT Fall 2026",
        description="Fall 2026 CPT I-20 (needed to bridge Aug 14 – Oct 1 gap).",
        required=False,
        doc_types=["i20"],
        keywords=["i-20", "i20", "ciam", "cpt", "fall", "2026"],
        filename_patterns=[r"^B13[_-]", r"ciam.*cpt.*fall", r"fall.*2026.*cpt"],
        order=13, phase="cpt_fall2026",
    ),

    # ─── C: CPT Academic Evidence ─────────────────────────────────
    Slot(
        id="C1", section="C", section_name="CPT Academic Evidence",
        title="CIAM Canvas evidence summary",
        description="Compiled exhibit: enrollments, grades, submissions.",
        doc_types=["academic_evidence"],
        keywords=["canvas", "cpt", "evidence", "academic"],
        filename_patterns=[r"canvas", r"academic.*evidence", r"cpt.*academic", r"^C1[_-]"],
    ),
    Slot(
        id="C2", section="C", section_name="CPT Academic Evidence",
        title="CIAM CPT training plan / application",
        description="CPT training plan form from DSO.",
        doc_types=["cpt_training_plan"],
        keywords=["cpt", "training plan", "application"],
        filename_patterns=[r"cpt.*(training|application)", r"^C2[_-]"],
    ),
    Slot(
        id="C3", section="C", section_name="CPT Academic Evidence",
        title="INT599 course syllabus",
        description="Internship course syllabus demonstrating course integration.",
        required=False,
        doc_types=["syllabus"],
        keywords=["int599", "syllabus", "internship"],
        filename_patterns=[r"int\s*599", r"syllabus", r"^C3[_-]"],
    ),

    # ─── D: Corporate (Petitioner) ────────────────────────────────
    Slot(
        id="D1", section="D", section_name="Corporate",
        title="Articles of Incorporation + SS-4",
        description="Formation docs + EIN application.",
        doc_types=["articles_incorporation"],
        keywords=["articles", "incorporation", "ss-4", "ss4"],
        filename_patterns=[r"articles.*incorp", r"ss[-_]?4", r"^D1[_-]"],
    ),
    Slot(
        id="D2", section="D", section_name="Corporate",
        title="Bylaws",
        doc_types=["bylaws"],
        keywords=["bylaws"],
        filename_patterns=[r"bylaws", r"^D2[_-]"],
    ),
    Slot(
        id="D3", section="D", section_name="Corporate",
        title="Corporate resolutions",
        doc_types=["corporate_resolution"],
        keywords=["corporate resolution", "resolutions"],
        filename_patterns=[r"corporate.*resolution", r"^D3[_-]"],
    ),
    Slot(
        id="D4", section="D", section_name="Corporate",
        title="SOI + Good Standing",
        description="Statement of Information + certificate of good standing.",
        doc_types=["soi", "good_standing"],
        keywords=["soi", "statement of information", "good standing"],
        filename_patterns=[r"soi", r"good.*standing", r"^D4[_-]"],
    ),
    Slot(
        id="D5", section="D", section_name="Corporate",
        title="Governance documents (signed)",
        doc_types=["governance"],
        keywords=["governance", "signed"],
        filename_patterns=[r"governance", r"^D5[_-]"],
    ),
    Slot(
        id="D6", section="D", section_name="Corporate",
        title="Key documents compilation",
        required=False,
        doc_types=["corporate_compilation"],
        keywords=["key documents", "compilation"],
        filename_patterns=[r"key.*documents", r"compilation", r"^D6[_-]"],
    ),
    Slot(
        id="D7", section="D", section_name="Corporate",
        title="EIN cancellation letter",
        description="Duplicate EIN cancellation.",
        required=False,
        doc_types=["ein_cancellation"],
        keywords=["ein", "cancel", "cancellation"],
        filename_patterns=[r"ein.*cancel", r"^D7[_-]"],
    ),
    Slot(
        id="D8", section="D", section_name="Corporate",
        title="EIN fax notification",
        required=False,
        doc_types=["ein_notice"],
        keywords=["ein", "fax", "notification"],
        filename_patterns=[r"ein.*fax", r"^D8[_-]"],
    ),
    Slot(
        id="D9", section="D", section_name="Corporate",
        title="Office lease",
        description="Commercial lease agreement (extract or full).",
        doc_types=["lease"],
        keywords=["lease", "office", "frontier", "commercial"],
        filename_patterns=[r"lease", r"frontier", r"^D9[_-]"],
    ),
    Slot(
        id="D10", section="D", section_name="Corporate",
        title="FTB withholding notice",
        required=False,
        doc_types=["ftb_notice"],
        keywords=["ftb", "withholding"],
        filename_patterns=[r"ftb", r"withholding", r"^D10[_-]"],
    ),
    Slot(
        id="D11", section="D", section_name="Corporate",
        title="Board resolution — signing authority",
        description="Establishes hire/fire authority (employer-employee).",
        doc_types=["board_resolution"],
        keywords=["board resolution", "signing authority", "hire", "fire"],
        filename_patterns=[r"board.*resolution", r"signing.*authority", r"^D11[_-]"],
    ),
    Slot(
        id="D12", section="D", section_name="Corporate",
        title="EIN CP575 notice",
        doc_types=["ein_notice"],
        keywords=["cp575", "ein"],
        filename_patterns=[r"cp[-_]?575", r"^D12[_-]"],
    ),
    Slot(
        id="D13", section="D", section_name="Corporate",
        title="Affidavit of financial support",
        required=False,
        doc_types=["affidavit"],
        keywords=["affidavit", "financial support"],
        filename_patterns=[r"affidavit.*financial", r"^D13[_-]"],
    ),
    Slot(
        id="D14", section="D", section_name="Corporate",
        title="Corporate bank statement",
        description="Petitioner ability-to-pay evidence.",
        doc_types=["bank_statement"],
        keywords=["bank statement", "corporate"],
        filename_patterns=[r"bank.*statement", r"^D14[_-]"],
    ),
    Slot(
        id="D15", section="D", section_name="Corporate",
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
        keywords=["registration", "draft", "yangtze"],
        filename_patterns=[r"registration.*(draft|confirm)", r"^E3[_-]"],
    ),
    Slot(
        id="E4", section="E", section_name="H-1B Registration",
        title="G-28 (secondary, if dual registered)",
        required=False,
        doc_types=["g28"],
        keywords=["g-28", "g28", "bsgc"],
        filename_patterns=[r"g[-_]?28.*(bsgc|secondary)", r"^E4[_-]"],
    ),
    Slot(
        id="E5", section="E", section_name="H-1B Registration",
        title="Secondary registration draft",
        required=False,
        doc_types=["h1b_registration"],
        keywords=["registration", "bsgc"],
        filename_patterns=[r"registration.*(bsgc|secondary)", r"^E5[_-]"],
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
        keywords=["formation", "wyoming", "llc"],
        filename_patterns=[r"formation", r"^F3[_-]"],
    ),
    Slot(
        id="F4a", section="F", section_name="Employment History",
        title="I-983 — STEM OPT employer #1",
        description="Signed I-983 training plan.",
        required=False,
        doc_types=["i983"],
        keywords=["i-983", "i983", "tiger"],
        filename_patterns=[r"i[-_]?983.*tiger", r"tiger.*i[-_]?983", r"^F4a[_-]"],
    ),
    Slot(
        id="F4b", section="F", section_name="Employment History",
        title="I-983 — STEM OPT employer #2",
        required=False,
        doc_types=["i983"],
        keywords=["i-983", "claudius"],
        filename_patterns=[r"i[-_]?983.*claudius", r"claudius.*i[-_]?983", r"^F4b[_-]"],
    ),
    Slot(
        id="F4c", section="F", section_name="Employment History",
        title="I-983 — STEM OPT employer #3",
        required=False,
        doc_types=["i983"],
        keywords=["i-983", "clinipulse"],
        filename_patterns=[r"i[-_]?983.*clinipulse", r"clinipulse.*i[-_]?983", r"^F4c[_-]"],
    ),
    Slot(
        id="F4d", section="F", section_name="Employment History",
        title="I-983 — STEM OPT employer #4",
        required=False,
        doc_types=["i983"],
        keywords=["i-983", "wolff"],
        filename_patterns=[r"i[-_]?983.*wolff", r"wolff.*i[-_]?983", r"^F4d[_-]"],
    ),
    Slot(
        id="F5a", section="F", section_name="Employment History",
        title="Unauthorized employer evidence — refusal",
        description="Evidence that employer refused to sign I-983.",
        required=False,
        doc_types=["correspondence"],
        keywords=["bitsync", "refused", "i-983"],
        filename_patterns=[r"refused.*i[-_]?983", r"bitsync.*refuse", r"^F5a[_-]"],
    ),
    Slot(
        id="F5b", section="F", section_name="Employment History",
        title="Unauthorized employer evidence — offer",
        required=False,
        doc_types=["offer_letter"],
        keywords=["bitsync", "offer letter"],
        filename_patterns=[r"bitsync.*offer", r"offer.*bitsync", r"^F5b[_-]"],
    ),

    # ─── G: Business Plans ────────────────────────────────────────
    Slot(
        id="G1", section="G", section_name="Business Plans",
        title="Petitioner business plan",
        description="Current business plan for petitioning entity.",
        doc_types=["business_plan"],
        keywords=["business plan", "yangtze"],
        filename_patterns=[r"business.*plan", r"^G1[_-]"],
    ),
    Slot(
        id="G2", section="G", section_name="Business Plans",
        title="Product/division business plan",
        description="Secondary plan (e.g. flagship product) reinforcing going concern.",
        required=False,
        doc_types=["business_plan"],
        keywords=["business plan", "guardian", "product"],
        filename_patterns=[r"guardian.*business.*plan", r"^G2[_-]"],
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
