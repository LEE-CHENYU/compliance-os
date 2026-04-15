"""Per-service rubrics defining the quality dimensions Claude will evaluate.

Each rubric has:
  - `dimensions`: list of (name, description) pairs that the judge scores
  - `context`: factual/legal grounding the judge should keep in mind
  - `version`: bumped when the rubric changes so cache invalidates

Rubrics are intentionally terse — we want the judge to exercise its own
expertise, not parrot our criteria back. Wording that's too prescriptive
biases the judge into checking for magic strings instead of evaluating.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Rubric:
    service: str
    version: str
    context: str
    dimensions: list[tuple[str, str]]


COMMON_DIMENSIONS: list[tuple[str, str]] = [
    ("correctness", "Is every factual claim in the output legally and regulatorily accurate? Flag anything that misstates IRS/USCIS/FinCEN rules, deadlines, thresholds, or filing requirements."),
    ("actionability", "Are the next steps specific enough that a self-directed user can execute them without guessing? Vague verbs like 'review' or 'confirm' without naming the target are red flags."),
    ("tone_severity", "Does the severity framing (critical/warning/info, 'URGENT', 'may be') match the actual consequence? Flag alarmism on minor issues and under-warning on serious ones."),
    ("completeness", "Does the output catch issues that a competent practitioner would catch, or miss obvious ones? Base this on what's in the output, not what's missing from the intake."),
    ("clarity", "Is the text understandable to a non-expert self-directed user (international student, first-time founder, early-stage employee)? Flag jargon without explanation and run-on findings."),
]


H1B_DOC_CHECK = Rubric(
    service="h1b_doc_check",
    version="1",
    context=(
        "H-1B Document Check reviews a user's uploaded H-1B petition packet and "
        "flags inconsistencies before filing. The packet typically has 5 documents: "
        "the USCIS registration record, a status summary, Form G-28 (attorney "
        "appearance), a filing invoice, and a payment fee receipt. Petitioners "
        "must be E-Verify enrolled (for STEM OPT continuity cases), entity names "
        "must match exactly across documents (Inc ≠ LLC is a USCIS rejection "
        "trigger), the signatory on the registration is usually the person "
        "authorized to act for the employer, and the FY2026 registration window "
        "ran Mar 7-25 2025 with petition filing window typically Apr 1-Jun 30. "
        "The user is likely a beneficiary without dedicated counsel."
    ),
    dimensions=COMMON_DIMENSIONS,
)


FBAR_CHECK = Rubric(
    service="fbar_check",
    version="1",
    context=(
        "FBAR (FinCEN Form 114) must be filed by US persons (citizens, residents, "
        "entities) whose aggregate maximum balance across foreign financial "
        "accounts exceeded $10,000 at ANY time during the calendar year. "
        "Threshold is strict — 'exceeded $10,000', not 'over $10,000'. "
        "Filing is through the BSA E-Filing System (not the IRS). The deadline "
        "is April 15 with an automatic extension to October 15 (post-2017 SAT). "
        "Penalties: non-willful up to ~$16K/year (2024 inflation-adjusted); "
        "willful up to greater of $129K or 50% of account balance. FBAR is "
        "separate from Form 8938 (FATCA), which has a higher threshold and goes "
        "to the IRS. The user is usually a non-resident student or worker with "
        "accounts back home."
    ),
    dimensions=COMMON_DIMENSIONS,
)


STUDENT_TAX_1040NR = Rubric(
    service="student_tax_1040nr",
    version="1",
    context=(
        "Nonresident students on F-1/J-1 file Form 1040-NR, not 1040. Form 8843 "
        "is required every year from exempt individuals regardless of income. "
        "Resident-return software (TurboTax, H&R Block, FreeTaxUSA) cannot "
        "correctly prepare 1040-NR — this routes users into wrong-form filings. "
        "China-US treaty Article 20(c) exempts up to $5,000/yr of student income "
        "(~22(1) for scholarships); India-US treaty lets students claim the "
        "standard deduction. Treaty claims must be supported by Form 1042-S from "
        "the payer and explicitly stated on the return. SSN or ITIN is required "
        "to file; without one the return will be rejected — Form W-7 requests "
        "an ITIN concurrently. The deadline is April 15 of the year following "
        "the tax year."
    ),
    dimensions=COMMON_DIMENSIONS,
)


ELECTION_83B = Rubric(
    service="election_83b",
    version="1",
    context=(
        "IRS §83(b) lets someone who receives restricted property elect to "
        "include the property's fair-market value in income NOW rather than as "
        "it vests. Common for startup founders and early employees receiving "
        "restricted stock. The election MUST be postmarked within 30 days of "
        "the grant date. Late elections are generally invalid and cannot be "
        "cured — there is no cure provision. A late filer should consult a tax "
        "advisor before taking action; mailing a late election is often "
        "pointless or counterproductive. The election mails via Certified Mail "
        "(proof of date) to the IRS service center matching the taxpayer's "
        "Form 1040 filing address. Post-2020 tax-year, a copy is no longer "
        "required to be attached to the taxpayer's annual return, but keeping "
        "a copy is still best practice."
    ),
    dimensions=COMMON_DIMENSIONS,
)


ALL_RUBRICS: dict[str, Rubric] = {
    r.service: r for r in [H1B_DOC_CHECK, FBAR_CHECK, STUDENT_TAX_1040NR, ELECTION_83B]
}


# Adversarial variants — same services, but dimensions role-play a skeptical
# adjudicator/examiner looking for reasons to reject a filing or assess a
# penalty. Different failure mode from the standard "is this helpful for
# the user" framing. Bumps the version so cache entries don't collide.

ADVERSARIAL_DIMENSIONS: list[tuple[str, str]] = [
    ("rejection_risk", "If the user follows this output verbatim, what are the concrete, named grounds (statute / reg / form instruction / adjudicator standard) on which USCIS/IRS/FinCEN could reject their filing or issue an RFE? Flag anything that sets the user up for a rejection."),
    ("penalty_exposure", "Does the output leave the user exposed to penalties that a careful practitioner would warn about — filing penalties, accuracy-related penalties, failure-to-file, willful vs non-willful distinctions? Flag missing warnings, not just wrong ones."),
    ("audit_trigger_signals", "Does the output guide the user toward choices that look like audit triggers — inconsistent entity names, wrong form version, zero withholding without estimated-tax payments, aggressive treaty positions without support? Name specific flags."),
    ("documentation_gap", "Adjudicators work from paper. Does the output instruct the user to keep the specific documents an adjudicator would demand if they audited — signed/dated copies, proofs of mailing, Form 1042-S copies, certified IDs for W-7, corporate records for 83(b) spread? Flag missing documentation requirements."),
    ("edge_regulatory_traps", "Are there quieter regulatory trapdoors this output walks the user into — Substantial Presence Test crossover, dual-status year, community-property-state treatment, state residency inconsistencies, AR-11 obligation, ITIN document-return timelines? Flag what an adjudicator would catch that the output doesn't."),
]


def _adversarialize(rubric: Rubric) -> Rubric:
    return Rubric(
        service=rubric.service,
        version=f"{rubric.version}-adv1",
        context=(
            rubric.context
            + " You are now evaluating from the perspective of a skeptical USCIS/IRS/FinCEN adjudicator "
            "or examiner whose job is to find reasons to reject filings, assess penalties, or open audits. "
            "You are not grading whether the output helps the user — you are asking whether following this "
            "output will expose the user to rejection, penalty, or enforcement risk."
        ),
        dimensions=ADVERSARIAL_DIMENSIONS,
    )


ADVERSARIAL_RUBRICS: dict[str, Rubric] = {
    service: _adversarialize(rubric) for service, rubric in ALL_RUBRICS.items()
}


def get_rubric(service: str, *, adversarial: bool = False) -> Rubric:
    return (ADVERSARIAL_RUBRICS if adversarial else ALL_RUBRICS)[service]
