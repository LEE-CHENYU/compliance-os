# Professional Tier List — Methodology

A reusable methodology for ranking professionals (attorneys, CPAs,
bankers, CAAs) by externally-verifiable credentials only. Ported and
generalized from the accounting project's
`attorney_external_credentials_tierlist_042326.txt`.

The core idea: **marketing copy produced by the firm itself is not
evidence of expertise**. A firm blogging about its own "success
stories" tells you what it wants you to believe, not what third
parties have validated. So we weight only signals that an uninvolved
third party has to issue.

## How this file is used

- **Sub-agent search prompts** (in `compliance_os/professional_search/personas.py`)
  embed the weighted-signals list so every persona applies the same
  standard when scoring firms.
- **Human review** of the ingested `v_attorney_comparison` / `v_vendor_comparison`
  views — when adjudicating close calls, re-check the `evaluations`
  table against this list.
- **Generalizing to other verticals** — swap in vertical-specific
  directories (e.g. for CPAs, replace Chambers with AICPA practice
  specialization; for banks, replace AILA with state banking
  commissioner enforcement history).

---

## Signals weighted (by approximate importance)

### Top-tier (strongest evidence of peer recognition)

1. **Chambers USA** — Band 1 / 2 / 3 / Senior Statesperson. Peer-
   ranked, editorially curated. For immigration, the "Immigration:
   Business" table is the target.
2. **AILA elected leadership** — Past National President, Chapter
   Chair, national Committee Chair. *Membership alone is not a
   signal* — tens of thousands of attorneys are members. Elected
   office is the signal.
3. **State Bar Certified Specialist** — e.g., California Certified
   Specialist in Immigration & Nationality Law (<200 attorneys hold
   this). Varies by state; always rare.

### Credible second-tier

4. **Best Lawyers in America** — peer-reviewed, category-specific
   listing. Self-nomination is possible, but final inclusion is peer-
   confirmed.
5. **AV Preeminent (Martindale-Hubbell)** — peer rating on legal
   ability + ethics.
6. **Super Lawyers** (state-specific) — peer-nominated with editorial
   selection.
7. **ABIL membership** (Alliance of Business Immigration Lawyers) —
   invite-only, <50 firms worldwide.
8. **IMMpact Litigation founding firm** — small set; strong signal for
   federal-court capability.

### Litigation-specific signals (if the matter may need federal court)

9. **Documented federal court filings** — verifiable via PACER (name
   of attorney as counsel of record).
10. **Counsel of record in reported AAO / federal decisions** —
    citable by case number.
11. **Government service alumni** — DOJ OIL, USCIS, etc., verifiable
    via resume or bar admission history.

### Academic / media signals

12. **Adjunct faculty at an ABA-accredited law school** — public
    listing on the school's website.
13. **Third-party media coverage** — WSJ, NYT, law reviews, ABA
    Journal. *Not* firm's own blog.

---

## Signals explicitly excluded

These are common sources of false confidence. They can be *noted* in
the evaluations table but should not move the tier.

- Firm's own blog posts, articles, "success stories" self-published.
- Self-described practice-area pages ("award-winning", "top-rated")
  without a cited third-party source.
- Podcast hosting on own platform.
- Amazon self-published books.
- "Featured in" claims without a verifiable outbound link.
- TechCrunch / Substack columns written by the attorney themselves.
- Sponsored / claim-able directory listings (Avvo claim pages, paid
  profiles).

## Scoring heuristic for `engagement.score`

Confidence returned by a search persona (0–100) maps to priority:

| Confidence | `priority` | Meaning                                              |
|-----------:|:-----------|:-----------------------------------------------------|
| 85+        | high       | Multiple top-tier signals; strong peer recognition   |
| 70–84      | medium     | At least one top-tier signal + credible second-tier  |
| 50–69      | low        | Second-tier signals only; include for breadth        |
| <50        | low        | Keep for comparison; unlikely final retention        |

The mapping is implemented in
`compliance_os/professional_search/ingest.py::_confidence_to_priority`.

---

## Firm-level vs individual-attorney credentials (CRITICAL)

A firm's Chambers / Legal 500 / Best Lawyers band is **not** the same as
the named lead_attorney's individual band, and the gap matters. A Band 1
firm can have Band 4 partners taking individual consults; the named
partner you book is not guaranteed to attend.

**The incident** (recorded for posterity): we paid $750 for a consult
with Robert F. Loughran at Foster LLP based on the firm's Chambers Band
1 (Texas Immigration) ranking. Loughran personally is Chambers Band 4
(2025) — two tiers below the firm. His specialty is EB-5 / L-1 / E-2 /
UHNW investor immigration, not H-1B owner-beneficiary. The substantive
consult quality reflected the gap, not the firm's headline credential.

**The rule for sub-agents:**

* **Stage 1 (preview):** any Chambers / Legal500 / Best Lawyers band you
  list MUST be the firm's band, not the named lead_attorney's individual
  band. Don't conflate them. If you only have firm-level evidence, label
  it that way ("Chambers USA Band 1 (firm)").

* **Stage 2 (paid enrichment):** verify the named lead_attorney's
  *individual* profile separately and surface the gap. The Stage 2
  enrichment runner (`enrichment_runner.py`) handles this — it asks per
  firm: "what is THIS named individual's personal Chambers/Legal500/Best
  Lawyers band, and which alternate same-firm partners fit the case
  better?"

* **UI obligation:** when individual_band − firm_band ≥ 2, the search
  results page renders a yellow "Routing risk: firm Band X / attorney
  Band Y" badge and surfaces alternate same-firm attorneys with their
  individual bands. The user gets the gap, not just the headline.

**Operational rule for users (intake template, not search agent):** in
every outreach reply to a firm, include: *"Which specific attorney
would attend the consultation? My case touches [issues]; I would prefer
the consult be with [Named Attorney 1 or Named Attorney 2] in that
order. I would prefer not to be routed to an unnamed associate."* And
re-confirm in writing 24-48 hours before any pre-paid consult.
