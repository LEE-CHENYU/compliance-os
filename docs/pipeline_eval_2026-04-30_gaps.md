# Pipeline eval — 2026-04-30 — gap analysis

Companion to `pipeline_eval_2026-04-30.md` (raw scores) and `.json`
(machine-readable). This doc interprets the run, ranks gaps, and
recommends what to fix before / during Phase 2 dogfooding.

## TL;DR

| Dim | Score | Bar | Verdict | Notes |
|-----|-------|-----|---------|-------|
| 1 Ingest reliability | 82.7% raw / **90.7% on positive controls** | 98% | FAIL | 4 real docs hard-rejected because filename classifier missed |
| 2 Classification accuracy | 93.0% | 85% | PASS | 3 mis-classifications — all driven by overly-greedy text patterns |
| 3 Dedup correctness | 100% | 100% | PASS | content-hash dedup works |
| 4 Index coverage | 100% | 95% | PASS | every accepted doc shows up in `/api/dashboard/documents` |
| 5 Finding extraction | **0 / 5** | 5 / 5 | FAIL | 43 real compliance docs uploaded, **zero** auto-findings produced |
| 6 Deadline extraction | 0 / 5 (rule-based deadlines: 1) | 5 / 5 | FAIL | the one deadline shown is rule-derived from tax category, not extracted from any doc |
| 7 Latency p50 / p95 | 5.7s / 10.2s | <30s | PASS | dominated by OCR for image-heavy PDFs (one Diploma_Columbia_Masters at 19s) |
| 8 Cost per 100 docs | n/a | baseline | — | classifier is local; OCR fallback fires on most PDFs |

**Phase 2 verdict:** **conditional green-light.** Ingest + dedup + index
are good enough to dogfood on cl4183 today. Findings/deadlines are
broken — but that's a feature gap, not a regression. Dogfooding with
broken findings will reveal whether the user *would* find them useful
if they existed, which is the better question for now.

## What broke (ranked by severity)

### S1 — `findings: list[0]` after 43 real compliance docs ingested

The biggest gap. The user uploads 4 W-2s, 4 1042-Ss, 2 tax returns, 4
paystubs, an I-94, an EAD-adjacent lease, an H-1B selection notice,
H-1B G-28s, an offer letter, transcripts, diplomas, bank statements.
The dashboard surfaces:

- 0 findings
- 1 deadline (the static "2026 Tax return due 2027-04-15" rule)
- 2 risk prompts ("FBAR — do you have foreign bank accounts >$10K total?", "Form 8938 — do you hold foreign assets >$50K?") — these are *category-presence prompts*, not extracted facts
- 39 integrity issues, all of shape `unchained_document` / `unmapped_document` (structural, not compliance)

In other words: the pipeline ingests + classifies, but does not *interpret*
the docs. The interpretation layer either isn't running for this user
or isn't wired to the dashboard for the eval shape.

**Repro path:** confirm whether `findings_router` / extraction job runs
on dashboard upload. If yes, it's silently producing nothing — debug
the prompt or schema. If no, the upload path is missing the post-ingest
hook. Spot-check whether `/api/checks/{check_id}/findings` returns
anything for the eval user's checks.

**Suggested next:** wire one toy finding (e.g. "I-94 admit-until-date
within 60 days") as an end-to-end smoke test before broader rebuild.

### S2 — Filename classifier rejects 4 real docs

These four uploads returned `400 Could not determine document type`:

| File | Should match | Why it didn't |
|------|--------------|----------|
| `2024_1099b_schwab_xxx619_part1.pdf` | `1099` | `1099` regex anchored with `[^a-z0-9]` on both sides — `1099b` has letter directly after `9`, breaking the anchor. (Note: misclassified, not rejected — see S3) |
| `2024_1099int_citibank_bsgc.pdf` | `1099` | same anchor bug; `1099int` doesn't match |
| `wf_personal_20251023_20260209.csv` | `bank_statement` | no path pattern for `bank_statements/wells_fargo/` directory; only matches `boa|citibank|wells_fargo` followed by a separator — but filename is just `wf_personal_*` |
| `CL_personal_engagement_letter_SIGNED_040626.pdf` | `legal_services_agreement` | regex catalog has no "engagement letter" pattern; only `fee_agreement`, `legal_services_agreement`, `retainer` |
| `columbia_degree_certification.pdf` | `degree_certificate` | regex matches `degree_certificate` literal, doesn't match `degree_certification` or `certification` alone |

**Fix sketch** (`compliance_os/web/services/classifier.py`):

```python
"1099": [
    r"(?:^|[^0-9])1099(?:[a-z]{0,4})(?:[^a-z0-9]|$)",  # tolerate 1099b/1099int suffix
],
# bank_statement PATH_CONTEXT_PATTERNS — add wells_fargo "wf_" filename:
r"/bank_statements/wells_fargo/wf_[^/]+\.csv$",
"legal_services_agreement": [
    ...,
    r"engagement[_ -]?letter",  # new
],
"degree_certificate": [
    ...,
    r"degree[_ -]?certificat(?:e|ion)",
    r"diploma_[a-z]+_(?:bachelor|master|phd|doctorate)",
],
```

Estimated impact: +5pp on dim 1 (positive controls), +2-3pp on dim 2.

### S3 — Text classifier hallucinates `identity_document` and `insurance_record`

Three confident-but-wrong classifications surfaced via OCR fallback:

| File | Expected | Got | Probable cause |
|------|----------|-----|----------------|
| `2024_1099b_schwab_xxx619_part1.pdf` | `1099` | `identity_document` | 1099-B forms have "Name", "ID Number" rows in the recipient block; `identity_document` text patterns are `Identification`, `ID Number`, `Date of Birth`, `Name` — many docs match incidentally |
| `schwab_llc_xxx239_2025_account_summary.pdf` | `annual_account_summary` | `identity_document` | same — Schwab account summaries include account holder identification block |
| `BSGC_engagement_letter_040626.pdf` | `legal_services_agreement` | `insurance_record` | engagement letters have "coverage", "member", "plan" boilerplate (e.g. "scope of representation", "engagement covers..."); these are exactly `insurance_record`'s text patterns |

**Root cause:** `identity_document` and `insurance_record` text patterns
are too generic — `Identification | ID Number | Date of Birth | Name`
matches the recipient block of nearly every form. Two-of-four match
trigger is too low.

**Fix sketch:**
- Add anchor patterns: `identity_document` should require `national_id`
  or `passport` or `driver_license` co-occurrence, not just "Name + ID Number"
- `insurance_record` should require `policy number` or `effective date`
  or `member id` co-occurrence
- Or raise `TEXT_MIN_MATCHES["identity_document"]` from 2 → 4

Estimated impact: +6pp on dim 2 (3/43 fixes).

### S4 — Markdown files rejected at MIME gate

`foster_consult_analysis_042726.md` returned `400 File type
application/octet-stream not allowed` — a different rejection from
the .txt files which return "could not determine doc_type". The .md
extension isn't in the allow-list.

This is mostly fine *for the eval* (negative control was rejected,
which is what we want for that file) but it's a bug: the rejection
reason should be "doc_type couldn't be determined", not "wrong MIME".
A user who legitimately wants to upload a .md note (e.g. a meeting
summary) hits this.

**Fix:** add `text/markdown` and `text/x-markdown` to the allowed mime
list, or fall back to "treat .md as text/plain".

### S5 — Latency dominated by OCR fallback on image-heavy PDFs

p95 = 10.2s, max = 67s on `3_Diploma_Columbia_Masters.pdf` (second-pass)
and 19s first-pass. This is OCR. For this fixture it's a non-issue
(below the 30s bar) but at 100+ docs it adds up.

**Fix sketch:**
- short-circuit OCR if filename classifies (already done in
  `_resolve_doc_type_for_upload_file`)
- but also: don't call OCR on docs >5MB unless filename failed
- the diploma is a scanned image — 5MB+ — so OCR is the only path

Defer this; it's a Phase 3 concern, not a Phase 2 blocker.

## What the eval doesn't cover (known unknowns)

- Performance with 1000+ docs — fixture is 52
- Concurrent uploads (dashboard ingests serially in this fixture)
- OCR failure modes (encrypted PDFs, broken pages) — `2024_w4_bitsync.pdf`
  ran 11s but classified correctly; encrypted PDFs *may* timeout differently
- Token cost per finding — moot until findings are actually being produced
- Cross-doc deduplication when filename differs but content is identical
  (this fixture has near-duplicates like `1098T_CIAM_2025.pdf` /
  `1098T_CIAM_2025_decrypted.pdf` — content hashes differ because
  decryption rewrites bytes, so dedup correctly does NOT collapse them.
  That's right behavior for this case)

## Phase 2 plan (no changes from original)

Green-light with the caveat: the user will see a busy data room with
zero findings on prod cl4183 too. That's the same result as local —
not a Phase-2-specific risk.

Pre-Phase-2 fix list (ordered by ROI):
1. **S2** classifier regex fixes — 1 hour, +5pp ingest, fewer false-rejections in prod
2. **S4** allow .md / fix mime gate — 15 minutes
3. **S3** anchor identity_document / insurance_record patterns — 30 min, +6pp accuracy
4. **S1** is the real product question — defer until we see what cl4183 actually wants surfaced

If we ship S2 + S4 only, ingest goes from 82.7% → ~92% and the worst
classification regressions stop firing.
