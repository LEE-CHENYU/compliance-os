# Cold-Start Onboarding Design — Guardian Claude Extension

**Date:** 2026-06-08
**Status:** Draft for review
**Surface:** The conversational Claude Code / Claude Desktop extension (local-first MCP), **not** the web wizard.
**Method:** 9-persona *blind* cold-start simulation (one agent role-played a confused real user, a second role-played the Guardian extension grounded only in the real 37 MCP tools, neither seeing the other's brief), followed by per-workflow product-UX review and cross-cutting synthesis with a completeness-critic pass. Reproducible from the saved workflow script (run `wf_ea5c7224-985`).

> **Provenance caveat.** The file:line references and tool-behavior claims below (e.g. `mcp_server.py:434`, "student_tax hardwires has_us_income=True", classifier label lists, template slot counts) are **simulation-derived assertions** produced by agents that read the codebase. They are load-bearing for the design and almost all checked out in spot-review, but **verify each against the actual code before implementing** — treat them as high-quality leads, not gospel.

---

## 0. The cold-start problem

A brand-new user installs the `.dxt`, opens Claude, and… there is no GUI wizard. They have 37 tools and an empty local state (no docs, no facts). The onboarding is therefore a *conversation the model improvises*. The question this spec answers: **what is the right improvised cold start — per workflow — that routes the user, collects the minimum to be useful, and delivers a first grounded result fast, without the model going off the rails?**

## 1. Headline finding — fabricated grounding is the real failure mode

Across all 9 simulated workflows, the **advice was substantively correct but the grounding was faked.** A capable Claude, dropped into a cold start with no rails, confabulates compliance authority: it narrates tool calls it never made, invents `run_compliance_check` types that don't exist (5472), quotes a wrong standalone deadline (8843 April-15 vs the code's June-15), ships a **self-fabricated wrong IRS address** on a deadline-critical 83(b) mailing, hallucinates *away* its single best capability (`lawyer_search_plan` → real named firms, the Priya-**D**), and twice never opens the one document the system exists to parse.

**Implication:** cold-start onboarding is not primarily "which questions to ask." It is **keeping a confident model on the rails of actual tool output, honest about its empty state, and honest about its real capability gaps.** That is the spine of every principle in §6.

## 2. Scorecard

| # | Workflow | Persona | Grade |
|---|----------|---------|-------|
| W1 | F-1 CPT authorization | Maya — F-1 CS masters, internship offer | B |
| W2 | Form 8843 (no-income student) | Raj — F-1 first-year, taxes confusion | B- |
| W3 | H-1B doc consistency / RFE risk | Wei — STEM OPT, H-1B selected | B- |
| W4 | Form 5472 / foreign-owned LLC | Diego — foreign-owned Delaware LLC | C- |
| W5 | Green-card stage / AP & AC21 | Anna — I-485 pending, needs to travel | B |
| W6 | Vague triage / possible status violation | Sam — "did I lose my status?" | B- |
| W7 | Professional search / attorney vetting | Priya — wants to vet an immigration attorney | D |
| W8 | 83(b) election (30-day clock) | Leo — early-exercise, 30-day 83(b) clock | C- |
| W9 | STEM OPT founder -> self-sponsor owner-beneficiary H-1B | Kenji — STEM OPT founder, self-sponsor H-1B | B- |

<details><summary>Full grade justifications</summary>

- **W1 Maya — F-1 CS masters, internship offer** — B. Excellent conversational reassurance and a correct, grounded first turn (legality + bright-line rule delivered immediately), but it cheated with false-precision claims about her email/I-20, corrupted its own fact store across two tracks, drip-fed batchable questions, stalled on the file-path UX, and never answered her named OPT-impact fear — the send-ready email arrived ~2 turns later than it should have.
- **W2 Raj — F-1 first-year, taxes confusion** — B-. First-value reframe in turn 1 was excellent and correctly routed; but the extension manufactured a false June-15 urgency the USER had to catch, presented hallucinated structured tool output the real code cannot produce, assumed an unverified 365-day count, and ended with placeholder-laden, unsaved forms it called 'ready to mail.'
- **W3 Wei — STEM OPT, H-1B selected** — B-: excellent trust-building and honest framing reached real first value in 2 turns, but it cheated by narrating fabricated structured parse/classify/scan outputs the tools don't produce, leaned on an unconfirmed OPT-type inference for its key reassurance, and silently dropped three checks (prevailing-wage dollars, worksite, identity fields) it had promised.
- **W4 Diego — foreign-owned Delaware LLC** — C-: correct workflow routing and an emotionally well-judged 'not auto-billed' reassurance reached fast, but first value was narrated rather than tool-grounded — both run_compliance_check calls were fabricated against non-existent check_types, the available entity rule engine / CPA 5472 template were never used, and the 'waiting doesn't increase exposure' framing contradicts the codebase's own cumulative/no-SOL rule.
- **W5 Anna — I-485 pending, needs to travel** — B — Correct, honest, well-paced legal triage that reached real first value in the target 2 turns and refused to fabricate the card's expiration; docked from A because the substantive answer is ungrounded in any Guardian tool, the extension implied doc-verification capabilities it does not have (no I-512/I-797/I-130 types; EAD schema is STEM-OPT-wired), and it never closed the verification loop it kept promising.
- **W6 Sam — "did I lose my status?"** — B-: substantively correct, genuinely calming, and right about the mechanism and repair paths by turn 4 — but it never parsed a single document, stalled 3 turns on the I-20, dressed ungrounded legal pathways as if tool-verified, and skipped the consult-an-attorney hedge its own instructions require for a critical status issue.
- **W7 Priya — wants to vet an immigration attorney** — D — The viability read was honest and well-framed and the anti-mill education was genuinely useful, but the extension hallucinated away its single most valuable capability (lawyer_search_plan → real named firms), never delivered the procurement deliverable the user asked for three times, simulated a non-existent compliance-check tool, and burned two turns on an irrelevant file hunt. It solved the problem it was comfortable with, not the one she had.
- **W8 Leo — early-exercise, 30-day 83(b) clock** — C-minus — Excellent tone, correct 83(b) substance (deadline, postmark, original-not-copy, $0 spread, H-1B is a non-issue) and a genuinely usable letter, but it shipped a WRONG, self-fabricated IRS address as its final deliverable on a deadline-critical mailing and narrated several tool calls it never made.
- **W9 Kenji — STEM OPT founder, self-sponsor H-1B** — B-: nailed routing, the hard-truth verdict, and the no-cheating-on-user-facts discipline, but leaned on unverified external cap-window/wage-lottery dates with false precision, never touched the document pipeline the user had ready, and mischaracterized the user's own private notes as a reusable repo playbook.
</details>

## 3. Universal cold-start opening (common to every user, before the workflow is known)

### Turn 1 — extension
*Purpose:* Reassure + set the local-first frame + state scope explicitly (so out-of-scope users can self-deselect early) + elicit the one-line problem WITHOUT a form. Invite the high-value disambiguators (money / date / document) up front, since a dollar figure or deadline alone can hard-route 83(b), AP travel, CPT, and 5472 in turn 1. NO tool call: READ-STATE is empty at cold start, and guardian_status returns a raw 'Error: ...' string if the local API is down (verified mcp_server.py:434) — calling it adds nothing and risks an ugly turn-1 error.

> "You're in the right place, and asking early is exactly how people avoid the real problems here — take a breath. Three things so you know how I work: (1) I run entirely on your own machine — nothing leaves your computer; (2) right now I'm a blank slate — I can't see your email, your files, or your situation until you tell me or point me at a document; (3) what I'm built for specifically is US filings for people on F-1 / H-1B / green-card-stage status, foreign-owned US companies (the 5472 trap), and startup-equity tax (83(b)). If your question is naturalization, asylum/TPS/DACA, a non-US country, or you're a US citizen, tell me — I'll say so honestly rather than guess. So, in a sentence or two: what's going on and what are you trying to figure out? And if there's a date or a dollar figure involved, mention it — that often tells me everything. (e.g. 'F-1 student, paid internship starting in 2 weeks'; 'foreign-owned US LLC, just heard about a 5472 penalty'; 'early-exercised startup stock, 30-day clock'; 'green card pending and I need to travel next month'.)"

### Turn 2 — extension
*Purpose:* Answer the actual fear in one line (deliver value BEFORE extracting) AND fire the single disambiguating routing question. For 5 of 9 workflows (5472, RCL, AOS/AP, EB-1A, founder) there is NO compliance check at all — run_compliance_check routes ONLY h1b_doc_check, fbar, student_tax, 83b_election (verified mcp_server.py:1214-1219). So for those flows the turn-2 'verdict' is the model's own legal reading, and the template must PHRASE it as such ('here's my read — not a computed check') so the UI doesn't over-credit the product. Still usually no tool call (no document yet).

> Pattern (CHECK-BACKED flows — 83(b), H-1B doc-check, student_tax, FBAR): "[One-line verdict tied to their words] — this is one I can actually run a check on — and the single thing that decides your path is: [the one disambiguating question]." Pattern (NO-CHECK flows — 5472, RCL, AOS/AP, EB-1A, founder, dependents): "Here's my read — and I want to be straight that this is my reasoning from the rules, not a number my tools compute: [one-line plain-language verdict]. The one thing that decides what we do next: [the one disambiguating question]." Example (F-1 + work): "Short version: yes, a paid internship is completely legal on F-1 — you just have to be authorized (CPT) before day one, and the bright line that protects you is: don't work a single day before the authorization start date. This is my read of the rules, not a computed check. The one thing that decides what we do next: is this someone else's company hiring you (normal CPT), or a company you own or co-founded (that's a different, trickier path)?"

### Turn 3 — extension
*Purpose:* ONLY if the turn-2 fork didn't fully resolve the workflow. Batch the 2-3 minimum routing facts in a SINGLE grouped ask (never drip one-per-turn). For any document-grounded workflow, offer the document path FIRST with an OS-CORRECT how-to (ask or detect OS — the macOS-only 'Copy as Pathname' string misfires on Windows), manual dictation as fallback. After this turn the workflow is committed and per-workflow specs take over.

> "Two quick things and I can [give you the verdict / draft the email / run the check]: (a) [routing fact 1], (b) [routing fact 2]. And if it's handy, the fastest path is to point me at [the one highest-leverage document] — on a Mac: right-click the file, hold Option, 'Copy as Pathname'; on Windows: hold Shift, right-click, 'Copy as path'; or just drag it into the chat. If that's awkward, no problem — read me the key lines instead and I'll work from that. (Which are you on, Mac or Windows? — so I give you the right instruction once.)"

## 4. Routing decision tree

Fires on the earliest unambiguous signal **cluster**, runs a silent scope gate first (fail *closed* — never into the nearest box), and disambiguates only genuine collisions.

```
OPENING SIGNAL  ->  WORKFLOW  (disambiguating question in [brackets])

Triage rule: route on the EARLIEST unambiguous signal CLUSTER, not a single keyword.
Never run a READ-STATE tool (guardian_status/documents/risks/deadlines) to "discover"
the user — state is empty at cold start AND guardian_status returns a raw "Error: ..."
string if the local API isn't running (verified mcp_server.py:434). Ask, don't probe.

═══ STEP 0: SCOPE GATE (run silently on every opener BEFORE routing) ═══
IN SCOPE: F-1/J-1/H-1B/green-card-stage status; foreign-owned US entity (5472);
          startup equity tax (83(b)); FBAR for the foreign-account personas.
OUT OF SCOPE -> graceful decline (do NOT route into the nearest box — the Priya failure):
  - US citizen / "I'm American" asking about themselves
  - naturalization / N-400 / citizenship test
  - asylum / refugee / TPS / DACA / removal/deportation defense
  - a country other than the US
  - 10-yr LPR with no pending action ("just renewing my green card")
  -> "That's outside what I'm built for. I cover F-1/J-1/H-1B/green-card-STAGE
      immigration, foreign-owned-entity tax (5472), and startup-equity tax (83(b)).
      For [naturalization / asylum / non-US / citizen] matters I'm honestly not the
      right tool — you'd want [an immigration attorney / USCIS.gov / a local
      professional]. I'd rather tell you that than give you confident wrong answers."

═══ STEP 0.5: DEPENDENT / PRINCIPAL GATE (catches the F-2/J-2/H-4 misroute) ═══
Signal: "F-2 / J-2 / H-4 / my spouse's visa / dependent / can my spouse work"
  [Are you the PRIMARY visa holder, or a dependent spouse/child?]
  Dependent -> [W10] dependent-status reasoning branch (honest: no dependent check
               or template exists; reasoning-only; H-4 EAD vs F-2/J-2 no-work rules
               differ materially — do NOT apply F-1 work rules to an F-2).

═══ ROUTING ═══

"F-1 / student visa" present
├─ + "work / internship / job offer / CPT / OPT"
│     [Is this someone ELSE'S company hiring you, or a company you OWN/co-founded?]
│        someone else's -> [W1] F-1 CPT/work-authorization
│        own/co-found    -> [W9] founder track  (ownership, NOT the H-1B keyword, is
│                                                the W1/W9 fork — see A2)
│     COLLISION with taxes: "Permission to WORK, or to FILE something with the IRS?"
│        Work -> W1. File -> tax branch.
├─ + "taxes / IRS / file something / TurboTax / 8843 / didn't earn money"
│     -> THREE-WAY income fork (NOT binary — see A1):
│        [Did you have (a) any WAGES/paid CPT-OPT, (b) any SCHOLARSHIP, STIPEND, or
│         grant of ANY kind, or (c) truly nothing but maybe bank interest?]
│        ├─ (c) truly nothing -> [W2] Form 8843 (no-income student)  ** do NOT call
│        │     run_compliance_check student_tax — student_tax_check hardwires
│        │     has_us_income=True and pushes an unwanted 1040-NR package **
│        ├─ (b) ANY scholarship/stipend -> HARD-ROUTE to student_tax / 1040-NR track.
│        │     Treat "scholarship" as a 1040-NR signal, NOT a soft one: a first-year
│        │     F-1 cannot reliably self-classify "scholarship above tuition" vs
│        │     "tuition waiver," and student_tax_check sums scholarship_income_usd.
│        │     A wrong "no income" here silently drops a required 1040-NR.
│        └─ (a) wages -> student_tax / 1040-NR track (run_compliance_check student_tax)
├─ + "dropped below full-time / only took 6 credits / under-enrolled / medical /
│      lose my status / did I lose status / SEVIS" -> [W6] status-violation triage (RCL)
│     COLLISION (under-enroll vs CPT): "Did you DROP classes, or ADD work?"
│        Drop -> W6. Add work -> W1.
└─ + "STEM OPT" + "own a company / pay myself / self-sponsor" -> [W9] founder

"J-1" present (do NOT treat as an F-1 synonym just because generate_form_8843
              accepts visa_type='J-1' — see E4)
├─ + "didn't earn money / 8843" -> [W2] 8843 (J-1 IS an exempt individual) BUT branch
│     the advice: flag 212(e) two-year home-residency exposure + J-1/J-2 work rules
│     differ from F-1 — reasoning-only, name the gap.
└─ + work/status question -> reasoning-only J-1 branch (no J-1 work-auth check exists).

"H-1B" present
├─ + "lottery selected / petition being assembled / RFE / specialty occupation /
│      I-983 + LCA + EAD doc set / does X contradict Y" -> [W3] H-1B doc-consistency
│     (employer's lawyer is filing; user wants a cross-doc audit)
├─ + "my own company / I own it / sponsor my OWN H-1B" ->
│     COLLISION W3 vs W9: "Is a petition already being FILED for you and you want the
│      documents audited (W3), or are you still deciding whether you even CAN
│      self-sponsor as the owner (W9 founder strategy)?"  Audit -> W3. Decide -> W9.
├─ + "my employer won't sponsor / self-petition / EB-1A / O-1 / extraordinary ability /
│      find & vet a lawyer" -> [W7] attorney-vetting (procurement)
│     COLLISION (doc-check vs attorney search): "CHECK your documents for consistency,
│      or HELP YOU HIRE a lawyer?"  Check -> W3. Hire -> W7.

"green card / permanent residency" present
├─ [Is Form I-485 actually FILED and pending INSIDE the US?]
│     NO -> CONSULAR-PROCESSING OFF-RAMP (see E2): "Then this is consular processing
│           abroad — different rules; Guardian's Advance-Parole / AC21 logic does NOT
│           apply. Travel questions there run on visa-bulletin / NVC mechanics —
│           reasoning-only, and I'll flag where you need a consular-savvy attorney."
│     YES -> continue:
├─ + "pending / advance parole / travel / fly to X / switching jobs / abandoning"
│     -> [W5] AOS travel-safety / AC21
├─ + "self-sponsor / EB-1A / O-1 / employer won't sponsor / hire a lawyer" -> [W7]
│     COLLISION: "Case already FILED and pending (protect it -> W5), or trying to
│      START a self-petition and hire counsel (-> W7)?"

"LLC / corporation / company" present
├─ + "foreign owner / I'm not American / I live abroad / single-member / 5472 /
│      Amazon seller" -> [W4] Form 5472 foreign-owned LLC
│     COLLISION (5472 vs founder-immigration): "About the COMPANY's US filings, or
│      about YOUR visa/work status?"  Company -> W4. Visa -> W9.
│     CO-TRIGGER (see A4): if foreign owner ALSO mentions a foreign bank account /
│      >$10k held abroad / FinCEN -> ALSO surface [W4b] FBAR (run_compliance_check
│      fbar is a REAL check) — same persona very often owes both.

"foreign bank account / >$10k abroad / FinCEN 114 / FBAR" present (standalone)
  -> [W4b] FBAR  (run_compliance_check('fbar', ...) — REAL check, was missing from
     the old tree despite being 1 of only 4 real checks)

"taxes / IRS / penalty / file something" (no visa context yet)
└─ disambiguate by entity: [Is this about YOU personally, a US COMPANY you own,
    EQUITY/stock you received, or a foreign BANK ACCOUNT?]
    ├─ personal + student visa -> 8843/student_tax THREE-WAY fork (F-1 branch)
    ├─ company + foreign owner  -> [W4] 5472  (+ FBAR co-check if accounts abroad)
    ├─ equity / restricted stock / early-exercise / "within 30 days" -> [W8] 83(b)
    └─ foreign bank account >$10k -> [W4b] FBAR

"restricted stock / early-exercised / options / 83(b) / 30 days" -> [W8] 83(b)
    (unique fingerprint: 30-day-from-private-grant clock; hard-route on turn 1)

FALLBACK (signal STILL ambiguous after turn 2, AND in scope): offer the named
workflow examples and let the user self-select. Do NOT silently route into the
workflow you're most comfortable with (Priya failure). If still unresolvable after
self-select, or if it smells out-of-scope, INVOKE STEP 0 decline rather than forcing
a fit.
```

## 5. Per-workflow onboarding specs

> W1–W9 map to the nine simulated personas in §2. **W4b (FBAR)** and **W10 (dependents — F-2/J-2/H-4)** are *derived branches* the completeness-critic surfaced as routing destinations, not separately simulated personas; they are specified here because the router must handle them.

### [W1] F-1 CPT / student work authorization

**Trigger signals**
- F-1 + paid internship/job offer at SOMEONE ELSE'S company
- the word CPT or OPT
- 'start in 2 weeks' + 'is this legal'

**Questions, in order**
- (turn-1 value, no question) 'Legal if CPT is authorized before day one; never work before the start date on the new I-20. This is my read of the rules, not a computed check.'
- OWNERSHIP fork FIRST (separates W1 from W9): 'Is this someone else's company, or one you own/co-founded?' If own -> hand off to W9.
- Batch: (a) when did you start your program; (b) is the internship tied to a course/curriculum yet; (c) read me the offer — employer, start date, hours; plus your full name + university. NOTE the DSO-email dependency: a SENDABLE email needs the I-20 (see firstValuableAction).
- Directly answer the carried OPT worry: part-time CPT does NOT reduce future OPT; only 12+ months FULL-time CPT eliminates OPT.

**Minimum facts**
- Visa = F-1 (not the owner of the hiring company — else W9)
- Degree level + field
- Program start / time in status (one-academic-year eligibility)
- Internship course-tied or not
- Intended start date
- Name + university (email body)
- I-20 (or DSO email read off it) — HARD dependency for a SENDABLE email, not just a draft

**First documents to request**
- Current I-20 (program start, SEVIS ID, assigned DSO name + DSO EMAIL via extraction_map ('i20','dso_email')) — without this the email has a blank recipient
- Internship offer letter (employer, start date, hours, paid)

**First valuable action (the "aha")**
Turn-1 legality verdict (labeled as reasoning) + bright-line 'no work before authorization' rule + the two eligibility gotchas (one-academic-year, curricular tie). THEN: if the I-20 is supplied (or the user reads the DSO email off it), a SEND-READY DSO email pre-filled with real DSO recipient + real facts; if NOT, be explicit it's a DRAFT with a [DSO email] blank, because the address comes only from the I-20 — there is no other source.

**Aha timing:** Turn 1 (reassurance + bright-line rule). Send-ready DSO email by turn 2-of-workflow ONLY if name+university+offer AND the I-20/DSO-email exist; otherwise a clearly-labeled draft-with-blank.

**Tools invoked**
- classify_document + parse_document on the I-20 (returns type=i20 + RAW first-page text; pull DSO name/email, program dates, SEVIS by READING the text via the i20 extraction map — parse_document does NOT emit structured fields)
- record_extracted_facts / set_user_fact (ONE track, e.g. track='f1_cpt' — do not split program_start across tracks)
- gmail_draft ONLY after a config probe: _gmail_guard returns 'gmail_not_configured' unless ~/.config/guardian/gmail_credentials.json exists (verified mcp_server.py:1285). DEFAULT promise = 'I'll draft it + give you the recipient; you send via your own mail connector.' Promise 'I'll send' only after the probe succeeds.
- calendar reminder (Google Calendar connector) for a 3-business-day DSO follow-up — actually create it if they say yes

### [W2] Form 8843 (no-income F-1/J-1)

**Trigger signals**
- F-1/J-1 + first year + 'didn't earn money' + 'file something with IRS'
- 'TurboTax kept asking for income I don't have'

**Questions, in order**
- (turn-1 reframe) 'That's Form 8843 — a one-page informational statement, NOT a tax return, for exempt individuals with no income. That's why TurboTax failed you.' Then the THREE-WAY income fork (see A1): 'Did you have (a) any wages/paid CPT-OPT, (b) any SCHOLARSHIP/stipend/grant of ANY kind, or (c) truly nothing but maybe bank interest?' (b) -> leave 8843 and HARD-ROUTE to 1040-NR; do not trust a blanket 'no income'.
- Exact first US entry date, and any departures/re-entries since (determines how many 8843s are owed — one per calendar year present). Do NOT assume days_present=365.
- Point me at your I-20/DS-2019 + passport, or give me: full legal name as on passport, country of citizenship, school name, US mailing address.
- Two fields: (a) any US status before this one? (b) SSN or ITIN, or neither? (neither is fine — leave blank, don't invent).

**Minimum facts**
- Visa = F-1 or J-1 (exempt individual)
- TRULY zero US income incl. NO scholarship/stipend (scholarship -> 1040-NR, not 8843)
- Exact first entry date
- Every calendar year physically present (one 8843 each)
- Country of citizenship
- School name (Part III)
- Full legal name
- US mailing address
- SSN/ITIN exists or not
- If J-1: flag 212(e) separately — not an 8843 field but a real exposure

**First documents to request**
- I-20 (F-1) or DS-2019 (J-1) — school name, SEVIS dates, sponsor (most of Part III)
- Passport bio page + visa stamp (legal name, passport #, country)
- I-94 / travel history (authoritative entry date + days-present, instead of assuming 365)

**First valuable action (the "aha")**
Turn-1 reframe (name 8843, 'not a tax return', required even at $0, that's why TurboTax broke) + the THREE-WAY income fork. Then generate the completed 8843(s) via generate_form_8843 and the concrete mailing mechanics (single-sided, ink signature, Austin service center, Certified Mail for any late year). DELIVERY HONESTY: generate_form_8843 returns pdf_base64 ONLY (verified mcp_server.py:1172) — there is NO MCP tool that saves it to a user-named folder. To land it on disk, the model must base64-decode and use a host file tool (Write/Bash); if the Claude surface is locked down and lacks those, say so plainly and hand the user the base64 / instruct them to use the web app's download — do NOT promise 'saved to your folder' when the toolset can't guarantee it (this is the C1 gap; until a save_artifact tool ships, the 'saved to disk' aha is conditional).

**Aha timing:** Turn 1 (the reframe dissolves the TurboTax panic). Generated PDF by the final workflow turn — and it must ACTUALLY land on disk via a host tool, or be honestly flagged 'returned as a file you download', never silently 'rendered, not saved'.

**Tools invoked**
- generate_form_8843(full_name, country_citizenship, visa_type, arrival_date, days_present_current, days_present_year_1_ago, school_name, tax_year, passport_number, us_taxpayer_id) — note days_present_current DEFAULTS to 0 (not 365); pass the real confirmed count. Returns pdf_base64 only.
- get_filing_guidance(form_type='form_8843', filing_with_tax_return=False, tax_year) — pass exactly 'form_8843' (the ONLY supported form_type, verified mcp_server.py:1263/1277)
- classify_document + parse_document on I-20/DS-2019/passport (real types: i20, passport; NO ds2019 label — DS-2019 will likely not classify, read it as raw text)
- Host file tool (Write or Bash) to base64-decode and save the PDF — NAME this fallback explicitly; it is the only save path and may be unavailable in a locked-down surface
- DO NOT call run_compliance_check student_tax for a zero-income user (hardwires has_us_income=True -> 1040-NR package)

### [W3] H-1B cross-document consistency / RFE risk

**Trigger signals**
- H-1B lottery selected + petition in progress (employer's lawyer filing)
- named doc set: I-20, EAD, I-983, pay stubs, draft LCA
- 'RFE', 'specialty occupation', 'maintenance of status', 'contradicts anything'

**Questions, in order**
- (turn-1 boundary framing) 'Here's the specific thing I do that's distinct from your lawyer: a local, field-by-field cross-document read — title/SOC/wage across I-983/offer/LCA, identity across IDs, OPT-end-to-H-1B-start timeline. Runs on your machine. The cross-doc comparison is ME reading the text, not a structured field-compare — I'll be explicit about what I could and couldn't read.' Then: confirm a petition is already being FILED for you (else this is W9 founder strategy).
- After scanning: report present-vs-missing, but HONESTLY against what the matcher returns — NOTE the H-1B template is NOT generic (verified: 30 columbia/ciam/westcliff references in h1b.py); slot titles are one real user's case and will be MEANINGLESS/PRIVACY-LEAKING for a new user. Until a sanitized generic template exists, do NOT run case_active_search('h1b') for arbitrary new users — operate reasoning-only on the docs they hand you. State the title/SOC/wage triangle from values YOU read in the raw text, naming any doc whose value couldn't be read (confidence is high-or-none, never a percentage). Confirm OPT type from the EAD category code (C03A vs C03B) you read, not from 'an I-983 exists'.
- For the timeline gap: collect all four anchors at once — EAD valid-from, current-employer true first day, prior OPT employer start+end, any unemployment before EAD start — and state the rule yourself (only zero-employment days count, aggregate across the whole OPT period, 90 initial / 150 STEM). There is NO unemployment-day calculator — label this as your reasoning.

**Minimum facts**
- A petition is actually being filed FOR the user (else -> W9)
- OPT type (initial vs STEM, from EAD category code read off the card)
- EAD/OPT valid-from
- Actual first day at current employer
- Every prior OPT employer's start/end + gaps
- Title+duties on I-983/offer/LCA, plus LCA SOC code + wage level — DICTATED or read from raw text (LCA has NO classifier label; cannot be auto-classified or field-extracted — see C4)

**First documents to request**
- Draft LCA (ETA-9035) — NOTE: no 'lca' classifier label exists; you'll read it as raw text only
- I-983
- Signed offer/support letter
- EAD card (category code + dates)
- Earliest pay stub

**First valuable action (the "aha")**
Read the documents the user hands you (parse_document raw text) and surface the genuinely attorney-missable finding — e.g. the job-title string differs across I-983 vs offer vs LCA, and/or the LCA is filed at Level I against substantive duties — delivered WITH an explicit list of what couldn't be read, and labeled as YOUR reading, not a structured cross-field compare. Optionally run_compliance_check('h1b_doc_check', inputs_json) which IS a real check (mcp_server.py:1215) — use it for the parts it covers rather than narrating a hand-computed verdict.

**Aha timing:** Turn 2 (turn 1 is an honest promise + scope; turn 2 delivers the first grounded flag from docs the user supplied).

**Tools invoked**
- run_compliance_check('h1b_doc_check', inputs_json) — REAL check; prefer it over a narrated verdict for the fields it computes
- parse_document (RAW first-page text only — narrate as text you read, NOT as 'Job Title: X / SOC: Y' fields)
- classify_document (real labels: i983, ead, i20, transcript, passport, w2, i94, cp_575; confidence is 'high' or None — NEVER a percentage; there is NO lca / lca_eta9035 label — do not invent one)
- set_user_fact for confirmed facts (one consistent track, e.g. 'h1b_petition')
- DO NOT run case_active_search('h1b') for a new user — the template leaks the original user's vendors (columbia/ciam/westcliff); the H-1B template has 48 Slot()s, not '60+'
- NOTE: no unemployment-day calculator exists — present 90/150 gap math as your own reasoning, labeled

### [W4] Form 5472 / foreign-owned LLC

**Trigger signals**
- single-member US LLC + foreign/non-US owner + lives abroad
- '5472' + 'big penalty'
- Amazon/e-commerce seller, 'no profit so I didn't file'

**Questions, in order**
- Is the LLC single-member (just you), and are you the only owner?
- Are you a non-US person (no citizenship/green card)? (confirms disregarded-entity treatment)
- Year formed, and which years had ANY activity (capital in, sales, fees, money out)? Even $0-revenue years count if you put money in.
- Do you already have an EIN (CP-575 letter, XX-XXXXXXX)?
- For each active year, have you filed anything at all?
- FBAR co-check (see A4): do you hold any non-US bank account that crossed $10k at any point? If yes, you likely also owe FinCEN 114 (FBAR) — that one I CAN run as a check.
- Drop your CP-575 + Certificate of Formation + any money-in/out record into one folder so I can read the legal name, formation date, EIN, and transaction amounts from the source.

**Minimum facts**
- Single-member LLC
- Foreign owner
- Tax years with reportable activity + entity year-end
- EIN exists or not
- 5472 filed-status per year
- Reportable-transaction amounts (the literal content of the form)
- Foreign-account exposure (FBAR co-trigger)

**First documents to request**
- CP-575 / EIN letter (classifies as cp_575 -> ein_letter; exact EIN + legal name)
- Delaware (or state) Certificate of Formation (legal name + formation date -> year-end + due date) — NOTE no classifier label for formation certs; read as raw text
- Bank statement / capital wire / Amazon disbursement (reportable amounts)

**First valuable action (the "aha")**
State the grounded obligation plainly, labeled as reasoning (foreign-owned disregarded entity must file 5472 + pro-forma 1120 even at $0 profit; trigger is reportable transactions, not profit), the honest penalty posture (NOT an auto-billed $25k; voluntary-correction path exists), and — critically — that for a multi-year non-filer, exposure ACCUMULATES per year with no statute of limitations (per the entity rule files). DO NOT run cpa_active_search for a new user (see toolsInvoked) — the CPA template is one real user's case. Instead enumerate the missing docs from the conversation + the docs they hand you. Also surface the FBAR co-check when accounts abroad exist.

**Aha timing:** Turn 2 ('not an auto-billed $25k, and here's the voluntary-correction fix'). Front-load the one-folder request in turn 2 — grounded extraction from the docs they hand you is the value, don't stall it.

**Tools invoked**
- run_compliance_check('fbar', inputs_json) IF foreign accounts >$10k — this REAL check is the one computable deliverable in this persona's orbit
- parse_document + classify_document on CP-575 (cp_575 -> ein_letter) and formation cert (formation cert has no label; raw text)
- set_user_fact (ONE consistent track, e.g. 'foreign_owned_llc')
- DO NOT run cpa_active_search(folder) for a new user — the CPA template (28 Slot()s) is hardcoded to the original user's entities (44 references: BSGC, VCV, BitSync, TD Ameritrade, Schwab, Wyoming). Slot titles like '2024 W-2 — BitSync' are meaningless to a new user and LEAK the original user's vendors. Reasoning-only until a sanitized 5472 template ships.
- NOTE: there is NO run_compliance_check('5472'), NO 5472 due-date/penalty engine in get_filing_guidance (form_8843 only), and NO 5472/1120 generator. Present due dates (15th day of 4th month after year-end) and the cumulative/no-SOL risk as reasoning grounded in the entity rule files, NOT as tool output. Do not promise 'I'll generate the exact 5472 fields'.

### [W4b] FBAR / FinCEN 114

**Trigger signals**
- 'foreign bank account' / '>$10k abroad' / 'FinCEN 114' / 'FBAR'
- co-triggered by W4 (foreign owner of US entity who also holds accounts abroad)

**Questions, in order**
- At any point in the year did the aggregate of ALL your non-US financial accounts cross $10,000 (even for one day)? FBAR is triggered by the aggregate high-water mark, not year-end balance.
- Which years, which countries/institutions, and max balance per account? (the literal content of the filing)
- Are you a US person for this purpose (citizen, green-card holder, or substantial-presence resident)? Note: many F-1/J-1 students are EXEMPT and may NOT be US persons yet — confirm before asserting an FBAR duty.

**Minimum facts**
- US-person status (don't assert FBAR on an exempt F-1)
- Aggregate crossed $10k in a given year
- Per-account max balances + institutions
- Years with a filing obligation

**First documents to request**
- Year-end / peak bank statements per foreign account (max balance)
- Nothing required to START — the check runs on stated max balances

**First valuable action (the "aha")**
Confirm US-person status FIRST (an exempt student often owes nothing), then run_compliance_check('fbar', inputs_json) — a REAL check — and return the verdict + the e-filing-on-BSA-E-Filing mechanics + the per-year deadline. Honest hedge: willful vs non-willful penalty posture is fact-specific; flag attorney consult if multiple high-balance years went unfiled.

**Aha timing:** Turn 2 (verdict from the real check). Turn 1 reassures + sets the $10k-aggregate mental model.

**Tools invoked**
- run_compliance_check('fbar', inputs_json) — REAL check (mcp_server.py:1216)
- set_user_fact (track='fbar')
- WebSearch/WebFetch only if a current filing deadline/threshold needs confirming; otherwise the check carries the mechanics

### [W5] Green-card stage: Advance Parole travel + AC21

**Trigger signals**
- 'green card pending' + a departure event (fly to X) and/or 'switching jobs'
- the word 'abandoning'
- I-485 / advance parole / combo EAD-AP

**Questions, in order**
- GATE FIRST (consular off-ramp, see E2): 'Is Form I-485 actually FILED and pending INSIDE the US?' If NO -> 'Then this is consular processing abroad — Guardian's AP/AC21 logic does NOT apply; different rules, and you'd want a consular-savvy attorney.' Do not fall through into AP logic.
- If YES: (a) family-based or employment-based? (b) Do you hold valid Advance Parole / combo EAD-AP, or are you on H-1B/L-1 (which has its own re-entry rules)?
- Exact depart/return dates, and the exact expiration PRINTED on the AP/combo card? (AP validity is judged at RE-ENTRY, not departure — and I cannot machine-verify the AP component, so read it to me.)
- Bundle the scary exception WITH its resolver: ever been out of status / overstayed 180+ days on any prior US stay, and was the I-485 filed while you were still in valid status?

**Minimum facts**
- I-485 actually FILED and pending IN the US (else -> consular off-ramp)
- Category (family vs employment)
- Travel-document status (valid AP / combo card vs work visa) + exact expiration READ BY USER
- Trip depart/return dates
- Unlawful-presence history; filed-in-status or not
- Job-change relevance (N/A for family-based)

**First documents to request**
- Combo EAD/AP card front+back — BUT honesty: classify recognizes 'ead' only; there is NO advance_parole/i512 type, and the EAD extraction map wires valid_to -> stem_opt_end_date (STEM-OPT-wired). You CANNOT auto-verify the I-512 AP component — ask the user to read the expiration aloud.
- I-485 receipt notice (I-797C) — NO i797 classifier label; will not classify; raw-text or manual set_user_fact only
- (Lower priority) I-130 receipt, marriage cert, passport for the I-94 admit-until date

**First valuable action (the "aha")**
By end of turn 2: the grounded go/no-go, LABELED AS REASONING (no AOS/AP/AC21 check exists) — travel on valid Advance Parole does NOT abandon a pending I-485 (that's its purpose), and AC21/job-change is employment-based and doesn't apply to a marriage case — with three honest caveats (validity judged at RE-ENTRY, carry the physical card, AP does NOT cure prior unlawful presence). MANDATORY consult-an-attorney hedge for ANY travel/status determination delivered WITHOUT document verification (which is most of W5, since there's no AP/I-512 classifier label) — not only when an overstay is disclosed (see D3): a clean-sounding 'go' that strands someone abroad on an expired card is the failure mode.

**Aha timing:** Turn 2 (the go/no-go). BUT honest that 'verified safe' requires reading the card, which the tool CANNOT ingest as an AP document — surface the attorney hedge regardless.

**Tools invoked**
- classify_document on the card — HONESTY FLAG: recognizes 'ead' but no advance_parole/i512 type; EAD valid_to wires to stem_opt_end_date. Cannot machine-verify the AP function — say so plainly.
- classify_document on the I-485 receipt — no i797/i130/marriage type; will NOT classify; do NOT promise structured 'I'll log your receipt + priority date' — at best raw text + manual set_user_fact
- set_user_fact (store AP expiration with an explicit 'verify before booking' flag) + create a Google Calendar entry for 'AP must be valid on [return date]'
- NO run_compliance_check for AOS/AP/AC21 — deliver as reasoning; MANDATORY attorney hedge (this is safety-critical travel); offer lawyer_search_plan if ANY prior overstay OR any un-verifiable card

### [W6] Vague status-violation triage (F-1 under-enrollment / RCL)

**Trigger signals**
- F-1 + 'dropped below full-time / only 6 credits' + fear of losing status
- 'did I do it wrong', 'SEVIS', 'am I going to be deported'

**Questions, in order**
- (one-line reassurance, labeled as reasoning) then exactly ONE fact: undergraduate or graduate? (sets 12 vs 9 credit threshold)
- The single fork: did your DSO/international office authorize the reduced load in SEVIS BEFORE you dropped, or did you drop the classes yourself?
- Point me at your I-20 the FIRST time with the OS-correct copy-path how-to (Mac: Option -> Copy as Pathname; Windows: Shift+right-click -> Copy as path; or drag in) so I read school, DSO contact, program dates, SEVIS ID straight off it — do not stall this 3 turns.
- Roughly when was the 6-credit term, and are you enrolled now or between terms?
- Send the clinic letter + transcript the same way so the DSO email cites real dates.

**Minimum facts**
- F-1
- undergrad vs grad
- DSO-authorized vs self-drop
- dated medical letter exists + whether submitted
- term timing + current enrollment
- I-20 fields: school, DSO email, program end date, SEVIS ID

**First documents to request**
- I-20 (DSO name+email, program end date, SEVIS ID, school)
- Clinic/medical letter (date matters for retroactive RCL or reinstatement)
- Transcript showing the 6-credit term

**First valuable action (the "aha")**
A ready-to-send DSO email framed as a help-seeking record-correction request (NOT a confession), pre-filled with the real school/DSO from the parsed I-20, PLUS the correct mental model (labeled as reasoning): medical RCL is legal only if DSO-authorized in SEVIS; this was a self-drop; the two repair paths are late/retroactive RCL via the DSO or I-539 reinstatement; act today. SENDABLE only if the I-20 supplied the DSO email — else a draft with a blank recipient (same dependency as W1). MANDATORY consult-an-attorney hedge: this is a critical status issue; do NOT overstate retroactive RCL as a probable clean fix.

**Aha timing:** Turn 1 reassurance; grounded sendable email by turn 2-of-workflow — TARGET 2 turns. Get the I-20 read instead of treating it as optional (the transcript stalled 3 times).

**Tools invoked**
- parse_document + classify_document on the I-20 (type=i20; read dso_name, dso_email, program_end_date, sevis_id from the text via the extraction map) — ACTUALLY call it; do not draft off a hazy 'a date I think is next year'
- set_user_fact (ONE track, e.g. 'f1_status'; if a value must change, call resolve_fact_conflict — do not write rcl_authorized twice)
- gmail_draft ONLY after _gmail_guard probe succeeds; DEFAULT = hand text + recipient and route through the user's own mail connector (do NOT promise 'I'll send it' by default — see D1)
- Google Calendar reminder for 'email DSO today' + fall-registration deadline
- MANDATORY attorney hedge (critical status issue); offer lawyer_search_plan if SEVIS termination/reinstatement is in play

### [W7] Attorney vetting / professional search (EB-1A self-petition)

**Trigger signals**
- 'employer won't sponsor' + 'self-petition' + EB-1A/O-1/extraordinary ability
- 'I do NOT want to do the paperwork — I want to HIRE a lawyer'
- 'find and vet a good lawyer'

**Questions, in order**
- (one-line confirm+reframe, STATE don't ask) 'You want to HIRE and compare real EB-1A/O-1 attorneys — I can actually search for named firms. EB-1A is the self-petitioned green card (your goal); O-1 is a temporary bridge. I'll vet for both.'
- Two facts to aim the search: (a) your field? (b) geography/jurisdiction preference + remote-OK, and a rough fee ceiling.
- Optional, NON-blocking: 'Point me at your CV and I'll sharpen the viability read — but I can give you the shortlist and a blunt verdict right now. Want me to just run it?'

**Minimum facts**
- Intent = procurement (hire+compare), not DIY — routes the whole session
- Vertical = immigration, employment-based / extraordinary-ability
- Field
- Geography / remote-OK
- Budget band
- Rough profile signals (enough for case_brief + viability read, NOT a 10-criteria audit)

**First documents to request**
- Nothing required — the search runs on a case_brief from stated facts, zero personal docs sent to the web
- Optional: CV path (parse_document) to sharpen viability — offered as an upgrade, never a gate

**First valuable action (the "aha")**
Call lawyer_search_plan(vertical='immigration_attorney' [confirmed default], personas=['employment_green_card','elite_boutique'], case_brief=..., purpose='EB-1A self-petition'), dispatch per-persona web-search prompts to sub-agents, ingest with lawyer_search_ingest(yaml_paths), return a ranked lawyer_tier_report('immigration_attorney') of REAL named firms (credential, source URL, fee band, why_fit) ALONGSIDE a blunt BORDERLINE viability verdict labeled as reasoning.

**Aha timing:** Turn 1-2: the named-firm shortlist is the deliverable she asked for three times. Do NOT claim you 'can't produce named firms' — lawyer_search_plan exists precisely for this. Do NOT burn turns on CV file-plumbing.

**Tools invoked**
- lawyer_search_plan (REAL; default vertical = immigration_attorney, confirmed mcp_server.py:1971 — surfaces real firms via web-search dispatch)
- Task/sub-agent dispatch of each persona prompt, then lawyer_search_ingest(yaml_paths), then lawyer_tier_report('immigration_attorney')
- parse_document on CV ONLY if a path is given — do NOT run h1b_active_search to 'find a resume' (wrong instrument)
- NOTE: no run_compliance_check('eb1a_readiness') — deliver the BORDERLINE verdict as honest reasoning, not a fabricated check

### [W8] 83(b) election (30-day clock)

**Trigger signals**
- '83(b)' + 'within 30 days'
- early-exercised options / restricted stock + 'file something with the IRS'
- unique fingerprint: 30-day-from-a-private-grant clock — hard-route on turn 1

**Questions, in order**
- Confirm workflow + lock the clock in one breath: 'This is an 83(b) — 30 calendar days from your exercise date, postmark controls, no extensions, H-1B doesn't block it. What was the exact exercise/transfer date?'
- 'Point me at your early-exercise agreement and I'll pull the numbers — or if not handy: shares, price/share, FMV/share at exercise.' (file path FIRST, numbers fallback)
- 'SSN or only ITIN?' — the one genuinely status-relevant detail.
- 'What state is your home address in?' — the 83(b) CHECK already maps state -> IRS service center.

**Minimum facts**
- Exercise/transfer date (anchors the 30-day deadline; postmark controls)
- Number of shares
- Exercise price/share
- FMV/share at transfer (spread = FMV - price)
- SSN vs ITIN
- Home state (the check derives the IRS service center — see C2)
- Nature of vesting/repurchase restrictions

**First documents to request**
- Stock purchase / early-exercise agreement (grant date, shares, strike, FMV, restrictions)
- Any company-provided 83(b) template (often not supplied)

**First valuable action (the "aha")**
Parse the agreement, run run_compliance_check('83b_election', inputs_json) — a REAL check — surface the spread (often $0 when FMV=price) AND the IRS mailing address the check itself emits from _STATE_TO_SERVICE_CENTER (e.g. CA -> Ogden, UT 84201-0002, verified election_83b.py), which already prints a 'Confirm on irs.gov before mailing' caveat (election_83b.py:210). Hand back the fully-drafted election letter + 30-day deadline + certified-mail proof steps. WebSearch is the FALLBACK only for the 'could not infer center' branch — do NOT mandate WebSearch as primary (the local check is correct; mandating an external lookup adds failure surface — see C2). DELIVERY HONESTY: the check writes PDFs to an INTERNAL ELECTION_83B_DIR/order_id/artifacts path the user never named (election_83b.py:220) — to put the letter where the user wants it, base64/copy via a host file tool and tell them the real path; do not claim 'saved to your folder' if you only have the internal path.

**Aha timing:** Turn 1 locks the deadline (panic -> countdown). Drafted letter + verified address by the final turn — with the save-location honesty above.

**Tools invoked**
- run_compliance_check('83b_election', inputs_json) — REAL check; actually call it (emits spread AND the state-mapped IRS address with its own irs.gov caveat)
- parse_document + classify_document on the agreement; record_extracted_facts
- WebSearch/WebFetch ONLY as a fallback when the check returns the 'could not infer center / look it up' branch (election_83b.py:217/277) — NOT as the mandated primary; do NOT hard-code Fresno/Ogden from memory
- Host file tool (Write/Bash) to surface the generated letter at a path the user names — the check's internal artifacts dir is not user-discoverable
- Google Calendar reminder to confirm the certified-mail green-card return

### [W9] STEM OPT founder -> self-sponsor owner-beneficiary H-1B

**Trigger signals**
- STEM OPT + 'started my own company' + 'I own most of it'
- F-1 + 'work at MY OWN startup' (even without the H-1B keyword — caught via the W1 ownership probe, see A2)
- 'pay myself a salary' + 'sponsor my own H-1B'

**Questions, in order**
- The single bright-line fact first: are you currently drawing W-2 wages / on payroll, or doing the work unpaid so far?
- Has anything been signed/sent to your DSO yet — a signed I-983, or have you been reported as employed here?
- Is the company E-Verify enrolled, and besides you, is there anyone (cofounder/officer/board) who actually controls/supervises you?
- Your EAD/STEM OPT end date, and entity type/state?
- (If a petition is ALREADY being filed for you -> this is partly W3; run the doc-consistency read too.)

**Minimum facts**
- Pay status (W-2 yet? — the bright-line violation trigger)
- E-Verify enrolled or not
- Any independent controller/supervisor (bona-fide employer)
- Ownership/control level
- STEM OPT start + EAD end date (runway)
- Entity type + state
- Signed I-983 on file or not

**First documents to request**
- EAD card (STEM OPT dates; real type=ead, valid_to->stem_opt_end_date)
- I-20 with STEM OPT recommendation
- The half-filled I-983 (confirm nothing signed/submitted)
- Cap table (controlling interest) — no classifier label; raw text
- Cert of incorporation + EIN letter (cp_575 -> ein_letter)

**First valuable action (the "aha")**
The grounded verdict, LABELED AS REASONING (no founder check exists): 'Today you're very likely NOT in violation — precisely because you haven't paid yourself and haven't signed/submitted an I-983, so authorized STEM OPT employment here hasn't started' — plus the hard truth that a 20% cofounder signing the I-983 does NOT cure the self-employment/bona-fide-employer problem, plus a this-week-vs-later sequence (don't sign the I-983; talk to DSO; get E-Verify; attorney-led restructuring). MANDATORY consult-an-attorney hedge (owner-beneficiary restructuring is a critical, structurally complex determination — D3).

**Aha timing:** Turn 2 (the not-in-violation verdict resolves the core fear). Ask the bright-line pay-status question FIRST, not buried under dense law.

**Tools invoked**
- parse_document + classify_document + record_extracted_facts on EAD (ead, valid_to->stem_opt_end_date), I-983 (i983), cp_575 — ingest the corpus on disk instead of running on conversation alone
- guardian_risks ONLY if documents were actually parsed — the stem_opt.yaml schedule_c_on_opt rule requires an EXTRACTED tax return; do NOT present a fired risk set when nothing was parsed
- lawyer_search_plan(personas including a founder/startup persona) for owner-beneficiary counsel — honestly flag that no founder-specific active-search template exists (case_active_search has only h1b + cpa, both of which leak the original user's data anyway)
- WebSearch/WebFetch to verify the CURRENT H-1B cap registration window before backward-planning — do NOT assert FY dates / wage-weighted-lottery rules from memory as settled law
- Do NOT cite the repo's internal founder_execution_timeline.md as a generic playbook — it's a private user doc
- MANDATORY attorney hedge

### [W10] Dependent status (F-2 / J-2 / H-4) — reasoning-only

**Trigger signals**
- 'F-2 / J-2 / H-4 / my spouse's visa / dependent'
- 'can my spouse work / study', 'will my status break if my spouse changes jobs'

**Questions, in order**
- Confirm: are you the PRIMARY visa holder or a dependent spouse/child? (If primary, re-route to the matching principal workflow.)
- Which dependent class — F-2, J-2, or H-4? (work rules differ sharply: H-4 may get an EAD in some cases; F-2 generally cannot work and has limited study; J-2 can apply for work authorization.)
- What's the underlying question — work, study, travel, or does the principal's job change affect you?

**Minimum facts**
- Principal vs dependent
- Dependent class (F-2 / J-2 / H-4)
- The specific action contemplated (work / study / travel)
- Principal's status stability (for derivative-status questions)

**First documents to request**


**First valuable action (the "aha")**
An honest, class-correct reasoning answer (e.g. 'F-2 spouses generally cannot work and can only study part-time; H-4 work needs a separate EAD tied to the H-1B principal reaching a green-card milestone; J-2 can apply for work authorization') with an explicit statement that NO dependent-specific check or template exists in Guardian, so this is reasoning-only — and an attorney/DSO referral for anything action-critical. Prevents the misroute into W1's F-1 work rules (E1).

**Aha timing:** Turn 1-2 (the class-correct correction is itself the value — it stops the user from applying the wrong rule set).

**Tools invoked**
- set_user_fact (track='dependent_status') for the facts gathered
- NO compliance check, NO case template, NO form generator exists for dependents — operate purely on reasoning, labeled as such
- Offer lawyer_search_plan if the question is action-critical (e.g. an H-4 EAD timing decision)

## 6. Cold-start principles (the rules the onboarding must enforce)

1. TRIAGE BEFORE ROUTE, VALUE BEFORE EXTRACTION. Turn 1 answers the user's actual fear in one grounded line (it's legal if X; not an auto-billed $25k; you have 12 days; AP travel doesn't abandon I-485) BEFORE asking for anything. Never open with a data-collection form. Every persona arrived panicking; the reassurance + bright-line rule IS the first value and it lands in turn 1.
2. STATE SCOPE IN TURN 1 SO OUT-OF-SCOPE USERS SELF-DESELECT, AND FAIL CLOSED — NEVER INTO THE NEAREST BOX. The opening names what Guardian covers (F-1/J-1/H-1B/green-card-stage, foreign-owned-entity 5472, 83(b), FBAR). For a US citizen, naturalization, asylum/TPS/DACA, a non-US country, or a settled green-card holder, run the explicit decline branch ('that's outside what I'm built for; you'd want X') rather than forcing a fit (the Priya failure). A graceful 'I'm not the right tool' beats a confident wrong answer.
3. ROUTE ON THE EARLIEST SIGNAL CLUSTER, NOT A SINGLE KEYWORD — AND USE OWNERSHIP/DEPENDENCY AS FORKS. Most personas are uniquely routable from sentence one. But ownership splits W1-vs-W9 (own company -> founder), not the H-1B keyword; principal-vs-dependent splits W1-vs-W10; I-485-filed-in-US splits W5-vs-consular. Fire the router immediately; spend a turn disambiguating ONLY when signals genuinely collide.
4. THE INCOME FORK IS THREE-WAY, AND 'SCHOLARSHIP' IS A HARD 1040-NR SIGNAL. A first-year F-1 cannot reliably self-classify 'scholarship above tuition' (taxable) vs 'tuition waiver' (not). student_tax_check sums scholarship_income_usd, so a blanket 'no income' that hides a stipend silently drops a required 1040-NR. Ask 'wages? / scholarship-or-stipend of any kind? / truly nothing?' and route any scholarship to 1040-NR, never to a clean 8843.
5. BATCH MINIMAL FACTS; NEVER DRIP ONE-PER-TURN. When several independent facts are needed, ask them in ONE grouped message labeled by purpose. Drip-feeding (the Maya/Diego failure) delayed the artifact ~2 turns each time.
6. DOCUMENT-FIRST WHERE A DOC IS THE SOURCE OF TRUTH, WITH AN OS-CORRECT HOW-TO AND A MANUAL FALLBACK. For form/audit/extraction workflows lead with 'point me at the file.' Give the copy-path how-to the FIRST time, OS-CORRECT (Mac: Option->Copy as Pathname; Windows: Shift+right-click->Copy as path) — ask Mac-or-Windows once; the Mac-only string misfires on Windows. Always offer drag-in / read-aloud. For PROCUREMENT (attorney search) the doc is NOT load-bearing — never gate the search on a CV. And note dependency: the DSO email address comes ONLY from the I-20, so without it the DSO email is a draft-with-blank, not sendable.
7. ACTUALLY CALL THE TOOLS YOU NARRATE; NEVER FABRICATE TOOL OUTPUT, AND LABEL REASONING AS REASONING. parse_document returns RAW first-page text only — narrate it as text you read, not as structured 'Job Title / SOC / Wage' fields. classify_document returns a type label + a binary confidence of 'high' or None (NEVER a percentage); the 'couldn't read it' signal is confidence=None or doc_type=None, not a low score. For the 5 workflows with NO check (5472, RCL, AOS/AP, EB-1A, founder, +dependents), the turn-2 verdict is YOUR reasoning — phrase it 'here's my read, not a computed check' so the UI doesn't over-credit the product.
8. KNOW WHICH CHECKS ACTUALLY EXIST. run_compliance_check routes ONLY h1b_doc_check, fbar, student_tax, 83b_election (verified). There is NO check for 8843-routing, 5472, RCL/reinstatement, AOS/AP/AC21, EB-1A readiness, or dependents — do not call those (they return 'Unknown check type') or simulate returns. get_filing_guidance supports ONLY form_8843. Surface FBAR proactively for the foreign-owner persona — it's a real check that was previously unrouted.
9. DO NOT RUN case_active_search FOR NEW USERS — THE TEMPLATES LEAK A REAL USER'S DATA. The h1b template (48 slots) has 30 columbia/ciam/westcliff references; the cpa template (28 slots) has 44 references to BSGC/VCV/BitSync/TD Ameritrade/Schwab/Wyoming, with slot titles like '2024 W-2 — BitSync'. These are one real user's case, meaningless and privacy-leaking to a new user. Until sanitized generic templates exist, operate reasoning-only on the docs the user hands you. (Correct count: H-1B 48, CPA 28 — not '60+'.)
10. HONESTY ABOUT EMPTY STATE AND CAPABILITY GAPS. State 'I run on your machine, I'm a blank slate, I can't see your files/email/situation until you show me.' Do NOT call READ-STATE tools to discover the user — they're empty and guardian_status returns a raw 'Error: ...' string if the API is down. Do NOT imply capabilities the tools lack: no Advance-Parole/I-512 type (the EAD valid_to is STEM-OPT-wired), no I-797/I-130/marriage/LCA/5472 classifier labels, no 5472/1120 generator, no unemployment-day calculator, no dependent or founder template. Name the gap.
11. CLOSE THE LOOP — BUT BE HONEST THAT SAVE-TO-DISK NEEDS A HOST FILE TOOL. generate_form_8843 returns base64 ONLY; process_election_83b writes to an INTERNAL artifacts dir the user never named; there is NO save_artifact MCP tool. To land a PDF where the user wants it, base64-decode and use a host tool (Write/Bash) and tell them the real path — and if the Claude surface is locked down without those, say so and hand them the download, never silently 'render, not save' (the Raj failure). Set reminders via the Google Calendar connector and actually create them when promised.
12. DEMOTE 'I'LL SEND THE EMAIL' TO 'I'LL DRAFT IT' BY DEFAULT. Guardian ships no Gmail OAuth; gmail_draft/gmail_send return 'gmail_not_configured' unless ~/.config/guardian/gmail_credentials.json exists. Default promise = 'I'll draft it and give you the recipient; you send through your own mail connector.' Escalate to 'I'll send' only after a config probe succeeds.
13. RECOMMEND A HUMAN AND OFFER THE SEARCH WHEN STAKES OR STRUCTURE DEMAND IT — AND THE HEDGE IS MANDATORY FOR UNVERIFIED TRAVEL/STATUS VERDICTS. DIY-appropriate: 8843, 83(b) mechanics, CPT email, 5472 form mechanics, FBAR, document consistency. The consult-an-attorney hedge is MANDATORY (not gated on a disclosed overstay) for ANY travel or status determination delivered without document verification — most of W5 (no AP classifier), W6 (critical status), W9 (owner-beneficiary restructuring) — because a clean-sounding 'go' on an expired card or a wrong RCL read strands someone. Offer lawyer_search_plan in those branches.
14. VERIFY VOLATILE EXTERNAL FACTS LIVE — BUT DON'T MANDATE A WEBSEARCH THE LOCAL TOOL ALREADY ANSWERS. For the 83(b) IRS address, use the address the run_compliance_check('83b_election') already emits from its state map (it prints its own 'confirm on irs.gov' caveat); make WebSearch the FALLBACK only for the 'could not infer center' branch. For H-1B cap windows and contested rules, DO use WebSearch/WebFetch and attach 'confirm on the source the day you act.' The single most damaging past cheat was a self-fabricated wrong IRS address — but the cure is the local check, not a mandated external lookup that may be unavailable.

## 7. Delta vs. the current 13-step web wizard

- CUT the standalone concern_area step (wizard 1) as a multi-select. The opening one-line problem statement carries the concern signal; infer and confirm in one line.
- ADD a scope gate the wizard has no slot for: turn 1 names what Guardian covers and the conversational router runs an explicit out-of-scope decline branch (citizen / naturalization / asylum / non-US). A static form cannot fail closed; the conversation must.
- ADD a principal-vs-dependent gate the wizard lacks: F-2/J-2/H-4 dependents route to a reasoning-only branch instead of being misrouted into F-1 work rules.
- KEEP and MOVE UP existing_help (wizard 2) — but only as a fork that matters: for attorney-vetting it's the WHOLE point (procurement vs DIY); for H-1B doc-check it sets scope ('I run underneath your lawyer'). Ask it where it changes the route, not universally.
- KEEP and SHARPEN timeline_urgency (wizard 3) into a per-workflow deadline anchor asked FIRST in deadline-driven flows (83(b) exercise date, CPT start date, AP return date, 5472 due dates), AND invite a date/dollar in turn 1 — a deadline or figure alone hard-routes 83(b), AP travel, CPT.
- COLLAPSE the visa-category cascade (wizard 4-6) from three sequential dropdowns into ONE routing signal + ONE disambiguating question. The conversation already names F-1/J-1/H-1B/green-card; don't re-ask it as a tree. But branch J-1 explicitly (212(e), J-1/J-2 work rules) rather than treating it as an F-1 synonym.
- REORDER the tax residency/income questions (wizard 7-10) so the SINGLE load-bearing fork — income — comes first, AND make it THREE-WAY (wages / scholarship-or-stipend / nothing) with scholarship as a hard 1040-NR signal. This splits 8843 from 1040-NR correctly where a binary fork silently mis-files a stipend.
- KEEP tax_entities (wizard 11) but turn it into a DOCUMENT request: request the CP-575 + Certificate of Formation and extract (cp_575 -> ein_letter) rather than typing entity fields. Grounded extraction beats re-typed facts.
- CUT corp_obligations (wizard 12) as a generic checklist; replace with the foreign-owner + single-member fork that routes to 5472, PLUS an FBAR co-check for foreign accounts — but do NOT run cpa_active_search to enumerate obligations (the CPA template leaks the original user's vendors); enumerate from the docs the user hands you.
- REPLACE the wizard's terminal summary screen (wizard 13) with a delivered ARTIFACT (filled 8843, send-ready-or-draft DSO email, ranked attorney shortlist, drafted 83(b) letter) — AND be honest that landing a generated PDF on disk needs a host file tool (no save_artifact MCP tool exists), and that the email is sendable only if Gmail is configured + the I-20 supplied the DSO address. End on something actionable, with truthful delivery caveats.
- ADD what the wizard has no slot for: (a) progressive disclosure of the empty-state/local-first frame + scope in turn 1; (b) a mandatory consult-an-attorney escalation for any unverified travel/status verdict; (c) live external-fact verification as a FALLBACK (cap window) while preferring the local check's own output (83(b) address); (d) the document-path-or-dictate offer with an OS-CORRECT copy-path how-to; (e) a consular-processing off-ramp and a dependent-status branch.
- NET REORDERING PRINCIPLE: wizard order is concern -> help -> urgency -> category -> details. Conversational order is scope-gate -> fear-answer (labeled as reasoning where no check exists) -> route (ownership/dependency forks) -> deadline-anchor -> minimal-batched-facts-or-document -> grounded-artifact-with-honest-delivery-caveats. Same information, value-first and triage-driven, failing closed on out-of-scope rather than into the nearest box.

## 8. Tool-layer prerequisites & blockers (must be resolved for the "deliver a grounded artifact" thesis)

These four gaps mean parts of the design are **currently unbacked by tools.** Each is listed with a proposed resolution; until resolved, the listed interim rule applies.

### 8.1 No `save_artifact` MCP tool (highest leverage)
`generate_form_8843` returns base64 only; the 83(b) generator writes to an internal `order_id` artifacts dir the user never named. There is no tool that lands a file at a user-named path, so every "saved to your folder" is conditional.
- **Proposed:** add `save_artifact(content_base64_or_text, user_named_path) -> real_path`; OR give `generate_form_8843` / the 83(b) generator an `output_path` param that returns the real path.
- **Interim rule:** the model base64-decodes and uses a host file tool (Write/Bash) and states the real path; if the surface is locked down, it hands over the base64/download and says so — never claims "saved" when it can't guarantee it.

### 8.2 Case-template PII leakage
`h1b.py` (48 slots, ~30 Columbia/CIAM/Westcliff refs) and `cpa.py` (28 slots, ~44 BSGC/VCV/BitSync/TD-Ameritrade/Schwab/Wyoming refs) are **one real user's case.** Running `case_active_search` for a new user leaks that user's vendors and emits meaningless slot titles ("2024 W-2 — BitSync").
- **Proposed:** build sanitized generic templates (`h1b_generic`, `5472_generic`, `founder_h1b`, `eb1a_evidence`, `dependent_status`); OR gate `case_active_search` behind a "user owns this case" check.
- **Interim rule:** **never call `case_active_search`/`cpa_active_search`/`h1b_active_search` for an arbitrary new user.** Operate reasoning-only on the documents the user hands you. (This blocks W3 and W4 from using their named active-search tools.)

### 8.3 `student_tax` hardwires `has_us_income=True`
It pushes a 1040-NR package, fighting the zero-income 8843 user (W2).
- **Proposed:** add a real no-income 8843 routing check; OR formally route $0 users straight to `generate_form_8843` and never call `student_tax`.
- **Scholarship edge:** treat any stipend/scholarship as a 1040-NR signal — a first-year F-1 cannot self-classify "scholarship above tuition" (taxable) vs "tuition waiver" (not), and `student_tax_check` sums `scholarship_income_usd`, so a blanket "no income" silently drops a required 1040-NR.

### 8.4 Classifier gaps block grounded extraction
`classify_document` recognizes i20/i983/ead/passport/transcript/cp_575/i94/w2 but **not** i797 / i130 / i485 / lca / ds2019 / advance_parole(i512). The EAD schema is STEM-OPT-wired (`valid_to -> stem_opt_end_date`) with no Advance-Parole field.
- **Proposed (priority by workflow unblocked):** `lca` (W3), formation-cert + `5472` mechanics (W4), `i485`/`advance_parole`/`i512` with its own schema (W5 — cannot machine-verify AP travel until this exists), `ds2019` (W2/J-1).

### 8.5 Supporting hardening (lower cost, high safety value)
- Add a clean empty-state return for READ-STATE tools (`guardian_status` returns a raw `Error: …` string when the local API is down) **and** an MCP-instruction rule: *do not call READ-STATE tools before a workflow is established.*
- Default Gmail to **draft + hand-off** ("send via your own connector"); escalate to "I'll send" only after a `gmail_not_configured` probe succeeds.
- Define a canonical `set_user_fact` **track taxonomy** (`f1_cpt, f1_status, foreign_owned_llc, fbar, h1b_petition, dependent_status, …`) and call `resolve_fact_conflict` on changes — the transcripts fragmented the source of truth across drifting track names.
- Enforce the **mandatory consult-an-attorney hedge** for any unverified travel/status verdict (W5/W6/W9) at the MCP-instruction level so it can't be skipped.

## 9. Open questions (carried from the synthesis; founder decisions)

1. SAVE-TO-DISK (highest leverage): the entire 'deliver an artifact' thesis is unbacked by tools — generate_form_8843 returns base64 only, process_election_83b writes to an internal order_id artifacts dir, and there is NO save_artifact MCP tool. Do we (a) add save_artifact(base64, user_named_path), (b) change the 83(b) generator to accept an output dir and return the real path, or (c) rely on the model shelling out to Write/Bash — which may not exist in a locked-down Claude Desktop MCP surface? Until one lands, every 'saved to your folder' promise is conditional.
2. CASE-TEMPLATE LEAKAGE: h1b.py (48 slots, 30 columbia/ciam/westcliff refs) and cpa.py (28 slots, 44 BSGC/VCV/BitSync/TD-Ameritrade/Schwab/Wyoming refs) are one real user's case. Running case_active_search/cpa_active_search for a new user leaks that user's vendors and produces meaningless slot titles. Do we build sanitized generic h1b + 5472 templates, or formally bless 'reasoning-only on user-supplied docs, never case_active_search for arbitrary users'? Until then W3/W4 cannot use their named active-search tools.
3. guardian_status returns a raw 'Error: ...' string when the local API is down (verified mcp_server.py:434), and nothing prevents the model from calling it reflexively at cold start (the server-level instruction even nudges toward checks). Do we (a) add a clean empty-state return so a stray call degrades gracefully, or (b) add an MCP-instruction-level 'do not call READ-STATE tools before a workflow is established'? Design relies on 'never call' as a hope, not a control.
4. Gmail in local-first defaults to the user's OWN connector (Guardian ships no OAuth unless ~/.config/guardian/gmail_credentials.json exists; gmail_draft/gmail_send return 'gmail_not_configured'). The design now defaults to 'draft + hand off,' escalating to 'send' only after a probe. Should the probe be an explicit tool, or do we just attempt gmail_draft and branch on the gmail_not_configured error?
5. student_tax check hardwires has_us_income=True and filing_with_tax_return=True, so it fights the zero-income 8843 user (emits a 1040-NR package). Do we (a) build a real no-income 8843 routing check, or (b) formally bless 'route 8843 directly, never call student_tax for $0 users' — and how do we handle the scholarship-ambiguous user who self-reports 'no income' but has a taxable stipend (the A1 silent-misfile risk)?
6. classify_document recognizes i20/i983/ead/passport/transcript/cp_575/i94/w2 but NOT i797/i130/i485/marriage/lca/ds2019/advance_parole/formation-cert. Which to add next, given they block grounded extraction for W3 (LCA), W4 (5472/formation cert), W5 (I-485/AP), W2 (DS-2019 for J-1)? The EAD schema is STEM-OPT-wired (valid_to->stem_opt_end_date) with no Advance-Parole field — an AP/I-512 card needs its own type/schema before W5 can machine-verify travel safety.
7. case_active_search has only 'h1b' and 'cpa' templates (both leaky). W9 (founder), W5, W7, W10 (dependents) have none. Do we add a startup_founder template (E-Verify, controlling-interest, governance slots), an EB-1A-evidence template, and a dependent-status template, or keep those reasoning-only?
8. For deadline-critical external facts (H-1B cap windows; not the 83(b) address, which the local check already supplies), is WebSearch/WebFetch reliably available in the user's Claude surface, and what's the fallback if not? Hard-coding from memory shipped a wrong CA address before — we need a sanctioned live-lookup-or-defer policy for the facts the local tools DON'T cover.
9. What's the canonical track/category taxonomy for set_user_fact? The transcripts drifted (f1_student vs immigration; tax vs foreign_owned_llc) and never called resolve_fact_conflict. A fixed per-workflow track map (f1_cpt, f1_status, foreign_owned_llc, fbar, h1b_petition, dependent_status, ...) would prevent fragmenting the source of truth.
10. Where should generated artifacts default to on disk, given there's no save_artifact tool and the 83(b) artifacts dir is internal? Is there a sanctioned Guardian data-room folder convention, or do we always ask the user to name a path and write there via a host tool?
11. For critical determinations delivered as reasoning (AP travel, RCL repair paths, founder not-in-violation, dependent work rules), what's the exact required hedge language, and should the mandatory-hedge-for-any-unverified-travel/status rule be enforced at the MCP-instruction level so it can't be skipped? The MCP instructions require a hedge for critical issues but the transcripts applied it inconsistently.
12. Should repo-internal docs (founder_execution_timeline.md, the original user's case files) be firewalled at the tool level from ever being surfaced to a user as product content? One transcript surfaced a private user doc as a generic playbook; outside users have no such file, and the case templates already leak vendor names through slot titles.

## Appendix A — per-workflow review highlights

### F-1 student work authorization — CPT (Curricular Practical Training) for a paid internship, time-boxed by a near-term start date. — B
- **Objective:** Maya needs to know whether she can legally take a paid part-time internship starting in ~2 weeks without wrecking her F-1 status or future OPT, and to get the one concrete next action (contact her DSO) done correctly and in time.
- **Earliest routing signal:** Turn 1, single sentence: "F-1 visa" + "paid part-time internship offer" + the literal word "CPT." Even the pair {F-1, internship offer} is enough to route to student work authorization before "CPT" is spoken. The universal router should fire on this triad immediately.
- **Where it cheated:**
  - Asserted her specific email format ('your @utexas.edu / @eid address') — it does not know her actual school email; this is a guess presented as fact.
  - Stated CPT is 'printed on page 2' of the I-20 as a certainty — true in general but presented with false precision about her future document.
  - Track/category drift across the fact store: turn 2 wrote facts to track='f1_student' / category='education'|'work_authorization'; turns 4-5 wrote the SAME logical facts (program_start, curricular tie) to track='immigration' with no category. This silently creates duplicate, conflicting fact records and never calls resolve_fact_conflict — a data-integrity defect, effectively hallucinating a clean single source of truth that doesn't exist.
  - Over-absolute reassurance: 'Pushing your start date is completely neutral... no penalty, no flag, nothing reported.' Stated as a guarantee about SEVIS behavior it cannot certify.
  - Loose equivalence: 'the one-year rule also generally counts as completed once you finish two full-time semesters' — conflates 'one full academic year' with 'two semesters' without grounding in her school's calendar, which it admits it doesn't know.
- **Friction:**
  - File-path dead-end: it asked for a 'file path' twice ('save it somewhere and tell me the file path') of a user who explicitly doesn't know what that is. Should have led with read-aloud / drag-the-file / 'which folder is it in' on first mention.
  - Drip-feed questioning: exactly 2 questions per turn is disciplined but here it stretched a single batchable data collection (name + university + offer details) across three extension turns, delaying the email artifact by ~2 turns.
  - Never attempted parse_document/classify_document or any READ-STATE call — the entire document and fact infrastructure went unused except set_user_fact; the offer letter was never ingested as a document, only transcribed verbally.
  - Repeated re-asking of facts already implied (re-stored program_start in turns 2,4,5) signals it wasn't trusting its own fact store.
  - Left the OPT-impact worry unanswered for all 5 turns despite it being one of her two core fears.

### Form 8843 for a no-income F-1 first-year student (standalone informational statement, mailed, not a tax return) — B-
- **Objective:** Raj needs to know what the IRS actually requires of a zero-income first-year F-1 student, and to get that thing (Form 8843) completed and correctly mailed before any deadline, without being dragged into a full tax return.
- **Earliest routing signal:** Turn 1, first sentence: "international student ... F-1 visa, first year ... didn't earn any money ... have to file something with the IRS by April." F-1 + first-year + zero income + "file something" is the unambiguous Form 8843 wedge — no further disambiguation needed to route.
- **Where it cheated:**
  - FABRICATED the run_compliance_check(student_tax) return. The real process_student_tax_check hardwires filing_with_tax_return=True and has_us_income=True (student_tax_check.py lines 429-430), so it ALWAYS builds a 1040-NR package with an April-15 deadline and CANNOT emit the simulated clean structured verdict (residency='nonresident_alien exempt individual', required_filings[] with per-year OVERDUE/not_yet_due status, form_1040NR_required=false, state_return='none'). For a $0 user it actually returns a 'student_tax_zero_income' warning saying 'this order may be more than you need.' The polished JSON shown to the model does not exist.
  - INVENTED a per-year residency/required-filings engine. Nothing in the tool computes 'one 8843 per present year,' marks 2024 OVERDUE vs 2025 not-yet-due, or asserts 'no penalty for a late 8843.' The model produced a correct-sounding multi-year analysis from its own knowledge and dressed it as tool output.
  - MIS-CALLED the tools it did invoke. generate_form_8843 has NO income, entry_date, us_address, or tax_year-as-shown params — the sim passed entry_date=, income=, us_address= (rejected) and never passed the real days_present_current/_year_1_ago params; it conflated 'days present' with 'form line 4a.' get_filing_guidance takes (form_type, filing_with_tax_return, tax_year) only and expects form_type='form_8843' not '8843' — the sim called it with '8843' and treated it as case-aware. set_user_fact is one key/value per call but the sim crammed multiple 'key=...; key=...' into single calls and showed an auto-assigned track that the call didn't set.
  - ASSUMED 2025 days-present = 365 (full year). Raj never said he stayed in the US the entire 2025 calendar year; a single trip home (very common for an Indian undergrad over summer/winter break) reduces the count. The model treated an unverified presence assumption as a hard form value. (The 136-day 2024 figure is correct arithmetic from the stated entry date.)
  - STATED as fact that NRA bank interest is 'tax-exempt and not even reportable' and that no 1040-NR is needed. This is generally true but was presented as a verified tool/IRS determination; no Guardian tool returned it — it is the model's own (here accurate) knowledge asserted with tool-grade confidence.
- **Friction:**
  - Turn-1 urgency error: the extension manufactured a false 'we have about a week (June 15)' deadline by assuming the user's first year was 2025, then had to retract it in turn 3 after the user themselves caught that they entered Aug 2024. A single early question ('what's your exact entry date?') would have prevented the scare entirely. The user, not the tool, did the disambiguation.
  - The model leaned on its own immigration knowledge while presenting it as tool output. Because the real student_tax tool would have pushed a 1040-NR package and an unhelpful 'this may be more than you need' warning for a $1 of interest, the well-reasoned answer is actually FIGHTING the tool rather than driven by it — a latent product gap, not a clean cold start.
  - Two-questions-per-turn pacing was good, but PII (legal name, full US address) was solicited via free-text dictation in turn 3 instead of offering 'upload your I-20 + passport and I'll read them,' which is the faster, lower-error, local-first path and would have also captured passport number and school address that were left as 'On file.'
  - Form shipped with placeholder Part III data ('On file' for school address/contact/program director) and a pending TIN, yet was described to the user as 'completed, ready-to-mail.' A form with literal 'On file' text in the institution line is NOT mailable as-is — the readiness claim overstated completeness.
  - No artifact actually landed: across the whole exchange the PDFs were 'rendered, not yet saved to disk,' the save location was still an open question at the end, and no reminder was set for the not-yet-due 2025 form — so the session ended with advice and an un-saved draft rather than a file in the user's hands.

### H-1B pre-filing cross-document consistency audit (RFE-risk reduction) for an F-1 STEM-OPT beneficiary transitioning to H-1B via change of status. Runs alongside, not in place of, the employer's attorney. — B-
- **Objective:** Wei wants Guardian to find any contradictions across his own H-1B source documents (title/SOC/wage and OPT employment-gap dates) that could trigger a specialty-occupation or maintenance-of-status RFE before the lawyer files the petition.
- **Earliest routing signal:** Turn 1, first sentence: "got picked in the H-1B lottery and they're putting together my petition" + named docs (I-20, EAD, I-983, pay stubs, draft LCA) + the words "RFE", "specialty occupation", "maintenance of status", "contradicts anything else." The combination of {H-1B + petition-in-progress + I-983/EAD/LCA doc set + "contradict"} uniquely identifies the h1b_doc_check / cross-document-consistency workflow on the very first message. No later turn is needed to route.
- **Where it cheated:**
  - FABRICATED STRUCTURED PARSE OUTPUT: parse_document in the real codebase (mcp_server.py:658) returns only raw first-page text from PyMuPDF. The transcript's tool returns — 'Job Title: Software Engineer. SOC/OES code: 15-1252 (Software Developers). Wage Level: Level I' for the LCA, and 'Job title: Data Engineer. duties: ... ETL ...' for the I-983 — are invented field-level extractions the tool does not produce. The extension narrated structured fields as if the parser returned them.
  - INVENTED A DOC-TYPE STRING: classify_document returns doc_type 'i983' and 'ead' from the classifier vocabulary (classifier.py:20,148,184). The simulated returns 'i983_stem_opt_training_plan' (conf 0.97) and 'lca_eta9035' (conf 0.95) are fabricated — there is no 'lca_eta9035' classifier type and 'i983_stem_opt_training_plan' is not the real label. The LCA classification with a precise confidence is hallucinated.
  - OVERSTATED h1b_active_search OUTPUT: the real tool runs match_folder against H1B_TEMPLATE (case_templates/h1b.py), which has 60+ slots (passport, I-94, twelve chronological I-20s, full corporate-formation set, business plans). A real scan of an 8-file folder would report a long list of missing template slots and filename-keyword match scores — NOT the clean 'present: 8 docs all read OK; MISSING vs template: offer/support letter + passport bio page.' The tidy 2-item missing list and the 'all files readable / classified' status were curated, not what match_folder returns.
  - PRESENTED OPT-GAP MATH AS TOOL-GROUNDED: there is no unemployment-day calculator anywhere in the codebase (no fact keys for unemployment days, no check_type for OPT gaps; cross_check.py only does fact-key mismatch/date-order/deadline checks). The 107-day / ~47-day / 90-vs-150 computation is the model reasoning by hand — legitimate as reasoning, but it was framed as if parsed pay stubs and the EAD drove it ('I parsed your earliest pay stub and it corroborates...'), blurring model arithmetic with tool output.
  - ASSERTED A SOC-TO-DUTIES MAPPING VERDICT ('data-engineering duties commonly map to 15-1252, substance is defensible') as a grounded finding. No tool in the system maps duties to SOC codes or evaluates specialty-occupation defensibility; this is the model's general knowledge, presented inside a 'from your actual docs' frame.
  - PAY-STUB CORROBORATION DETAIL: 'Pay period begins mid-October 2023; first paycheck issued late October 2023; employer matches current employer on offer letter/LCA' is a fabricated structured parse return — parse_document would yield raw text, and matching the employer across documents is an inference, not a tool result.
- **Friction:**
  - The first valuable output is gated behind the user supplying a folder path — unavoidable and correct (local-first, empty at cold start), but it means turn 1 produces zero findings, only a promise. That promise was unusually well-constructed, so it landed.
  - The gap math was delivered piecemeal across two turns: turn 2 asked for EAD start + current-job start; turn 4 then revealed the aggregate-across-whole-OPT-period rule and asked for the prior-job dates and pre-EAD gaps. A user could have surrendered the prior-OPT-job dates in turn 2 if the four timeline anchors had been requested together up front. One extra round-trip of latency.
  - The extension repeatedly asks the user to confirm or read dates off the EAD ('low-confidence OCR on day digits') — realistic, but it shifts OCR work onto the user and slightly undercuts the 'I parsed your files' claim.
  - Skepticism friction: the user explicitly doubts a tool helps when a lawyer is on it. The extension's framing defused this, but every turn still carries the burden of justifying its existence relative to the attorney, which costs words.
  - No verification that the OPT type was actually confirmed before relying on the 150-day ceiling — the reassuring 'even worst-case 107 < 150' conclusion rests on an inference ('I-983 present implies STEM') the extension itself flagged as unconfirmed, then leaned on anyway.

### Form 5472 / pro-forma 1120 late-filing remediation for a foreign-owned single-member Delaware LLC (foreign-owned disregarded entity). — C-
- **Objective:** Diego, a non-US (Brazil) owner of a Delaware single-member LLC selling on Amazon, needs to know whether he has a Form 5472 filing obligation, how exposed he is to the $25k penalty given he filed nothing for 2024 (and 2025), and the concrete DIY steps to get compliant.
- **Earliest routing signal:** First user message: "single-member LLC in Delaware" + "I live in Brazil and I'm not American" + "5472 form thing." The combination foreign owner + single-member US LLC is the unambiguous entity-track / 5472 router signal — present in turn 1, before any tool call.
- **Where it cheated:**
  - FABRICATED TOOL OUTPUT: called run_compliance_check(check_type=foreign_owned_de_5472) and again (check_type=5472_foreign_owned_de). Neither check_type exists — mcp_server.py routes run_compliance_check ONLY to h1b_doc_check, fbar, student_tax, 83b_election. The real return is {"error":"Unknown check type"}. The extension invented detailed JSON returns (required_forms, due dates, a penalty object with auto_billed/compounds flags, abatement-odds notes) and presented them as grounded tool results.
  - INVENTED A DUE-DATE/PENALTY ENGINE: the precise '15th day of 4th month → April 15, extended Oct 15 via 7004' and the structured penalty posture were narrated as if computed by the check; no MCP tool computes 5472 due dates or penalty posture (get_filing_guidance supports only form_8843; there is no 5472 deadline tool exposed).
  - CONTRADICTED ITS OWN CODEBASE ON PENALTY DYNAMICS: asserted 'the penalty window does not close against you by waiting — and it does not get worse on a daily clock either... flat, not compounding.' The codebase rule cumulative_5472_penalty states the opposite for a multi-year non-filer: 'penalties accumulate for every year since formation... There is no statute of limitations.' Framing exposure as static understates a cumulative, SOL-unbarred risk.
  - PROMISED UNBACKED CAPABILITIES: 'I'll generate the exact fields for you' and 'I'll lay out both years' 5472 packages' imply a 5472/pro-forma-1120 generator. No such tool exists (generate_form_8843 is the only form generator; get_filing_guidance only supports form_8843).
  - ASSERTED A SPECIFIC FILE PATH AS A SYSTEM CONVENTION: instructed the user to create ~/guardian/llc-5472/ as if Guardian watches/ingests it. No tool establishes or monitors that path; batch_upload/cpa_active_search take an arbitrary folder arg — the named path is invented convention.
- **Friction:**
  - Asked for facts conversationally (formation year, EIN existence) when the authoritative source — CP-575 + Certificate of Formation — should have been requested FIRST so the real legal name/date/EIN could be extracted, not re-typed and approximated.
  - Delivered three dense walls of text (turns 2/4/6) heavy on tax exposition before any grounded artifact; high reading load for an anxious, non-native-English, different-timezone user.
  - Stalled at the gather-files boundary at the END of the conversation (turn 6) rather than front-loading the one-folder request in turn 2 — pushed the only grounded step (document extraction) to after three turns of talk.
  - Surfaced the 2025 second-year obligation reactively (only after the user volunteered full-year 2025 sales) instead of asking 'which years had activity' up front — the multi-year scope emerged piecemeal, amplifying the user's $50k scare in steps.
  - Recorded facts with inconsistent track tags (set_user_fact stored track 'tax' in turn 4 but 'foreign_owned_llc' in turn 6) — fragmented state that would confuse later get_user_facts(category,track) reads.
  - Never ran cpa_active_search even after the user agreed to assemble a folder — the one tool purpose-built to tell him exactly which 5472 docs are missing went unused.

### Green-card stage: Advance Parole travel-safety + AC21/job-change abandonment risk check on a pending marriage-based I-485 (Adjustment of Status) — B
- **Objective:** Anna wants a trustworthy yes/no on whether she can take a short Toronto trip in ~5 weeks and change jobs without "abandoning" her pending marriage-based green card, before she spends money booking and accepts the offer.
- **Earliest routing signal:** Turn 1: co-occurrence of "green card application pending" with a departure-from-US event ("fly to Toronto") and/or "switching jobs," plus the word "abandoning." That triple is the unambiguous AOS / Advance Parole / AC21 router trigger.
- **Where it cheated:**
  - Turn 3 the extension promised, on uploading the combo card, to 'confirm it's a true combo (C9 EAD + AP) card' and read the AP expiration. The codebase has NO Advance Parole / I-512 doc type and the `ead` extraction schema (compliance_os/facts/extraction_map.py:51-55) maps the card's `valid_to` to `stem_opt_end_date` and `category` to `current_immigration_status` — wired for STEM OPT. There is no field that captures or verifies the I-512 AP component, so the promised 'confirm it's a true combo' verification is not backed by any tool. This is a capability the extension implied it has but does not.
  - Turn 3 also promised 'If you also drop the I-485 receipt notice, I'll log your receipt date and priority date while I'm at it.' classify_document supports 115 doc types but NONE for I-485/I-797C (no `i797`), I-130, or marriage certificate (verified: only `ead` and `passport` among Anna's five docs are recognized). So the I-485 receipt would not classify, and 'log your receipt date and priority date' is not a backed structured-extraction path — at best raw-text reading + manual set_user_fact.
  - Across all turns the substantive legal conclusions (AP travel doesn't abandon I-485; AC21 is EB-only; no unlawful presence ⇒ no 3/10-year bar) are delivered as Guardian output but come entirely from the model's own legal knowledge. There is NO run_compliance_check, rule YAML, or guidance tool covering AOS/AP/AC21 (checks are only h1b_doc_check, fbar, student_tax, 83b_election). The answer is correct, but it is ungrounded-in-tooling and presented with more institutional authority ('the sanctioned, intended way') than the product's verifiable surface supports — a softer form of cheating: borrowing the product's trust for an un-checked legal opinion.
  - Minor: the I-512 reassurance 'it literally says Serves as I-512 Advance Parole' (turn 3) asserts specific card wording before the card was ever seen — stated as fact about HER card rather than as 'a true combo card will say.' Low harm because it later asked to verify, but it momentarily presented assumed card text as confirmed.
- **Friction:**
  - Repeated 'upload the files and I'll verify' loop that never closed: the extension asked for the card path in turn 2 AND turn 3, scanned Desktop, found nothing, and ended the cold start still blocked on an offline user action — the promised 'verified green light' was dangled three times and never delivered. An anxious, time-pressured user is left at 'very likely safe' indefinitely.
  - Caveat whiplash: turn 2 raised the unlawful-presence 3/10-year bar as a scary exception, which (per the user's own internalState) 'reignited her fear' and consumed an entire extra round-trip (turn 3) to walk back. Naming it was responsible, but it should have been bundled WITH the disqualifying question ('have you ever overstayed 180+ days?') in the same breath, so the scary thing and its resolution arrive together rather than the fear landing first and the relief a turn later.
  - The doc pipeline can't actually ingest 4 of Anna's 5 documents (no I-797/I-130/marriage-cert types; AP card misread as STEM-OPT EAD). So even if she had pasted the path, the 'verified' experience the extension sold would have partially failed or produced wrong-track facts — friction that is invisible to the user but baked into the product.
  - Verbosity under time pressure: each extension turn is long. For an anxious user wanting a clear yes/no, the lead answer is good (bolded top-line) but the three-caveat + two-question + file-request stack at the end of every turn is heavy and re-opens anxiety loops.
  - set_user_fact stored advance_parole with flag 'expiration_unverified' but the conversation never resolved that flag — the open risk just sits in state with no deadline, reminder, or follow-up mechanism surfaced to the user (e.g. no guardian_deadlines entry for 'AP must be valid on 2026-07-17' or 'verify card before booking').

### Vague triage of a possible F-1 status violation (medical under-enrollment / unauthorized Reduced Course Load), cold start with no prior state. — B-
- **Objective:** An F-1 undergrad who self-dropped below full-time for medical reasons without DSO authorization wants to know whether she has lost status and exactly what to do next to fix it.
- **Earliest routing signal:** Turn 1, first sentence: "only took 6 credits ... on a student visa and I could lose my status." The pairing of {F-1/student visa} + {dropped below full course load} + {fear of losing status} is the unambiguous earliest trigger and should route to the F-1 under-enrollment / RCL triage workflow before any document is seen.
- **Where it cheated:**
  - NO document was ever parsed, yet the extension repeatedly implied document-grounded capability ('I'll pull your actual school, DSO name/contact, program level, program start/end dates straight from it'). That is a promise, not a cheat — but by turn 4 it drafted a near-final DSO email and called the workflow done WITHOUT a single parse_document/upload_document call, so every 'real' fact still came from the user's mouth, not the I-20. It dressed up an ungrounded result as grounded.
  - In turn 4 reasoning it asserts 'the program-end date being next year suggests the I-20 hasn't expired, which is good' — but it never read the I-20; it is interpreting the USER's vague 'a date I think is like next year sometime' as if it were an extracted field. That is treating a hazy user recollection as a verified document fact.
  - The extension confidently routes to two specific legal remedies — 'retroactive/late medical RCL' and 'Form I-539 reinstatement' — but the Guardian toolset has NO RCL or reinstatement or I-539 compliance check (run_compliance_check only supports h1b_doc_check, fbar, student_tax, 83b_election). So the legal pathway is generic model knowledge presented in Guardian's authoritative voice, with no tool grounding and no consult-an-attorney hedge surfaced to the user despite the MCP instructions requiring it for critical issues.
  - It states retroactive medical RCL is something the DSO 'sometimes can still apply' and frames it as a likely best outcome ('quietly fix the record'). Retroactive RCL is, in practice, rarely available — RCL must generally be authorized before dropping below full-time. Presenting it as a probable clean fix overstates a favorable outcome the extension cannot verify.
  - track names drift across tool calls ('immigration' in turns 1-2, then 'f1_status' in turn 4) — the extension is writing facts to inconsistent tracks, which would fragment the source of truth it claims to be building.
- **Friction:**
  - The I-20 path request was made three times and stalled three times. When the user said 'I don't know how to drag it in,' the extension's turn-3 reply still didn't give the copy-path instruction — it only appeared in turn 4, buried and marked 'totally optional.' Three turns of friction to extract one path that the whole grounding story depended on.
  - By framing the I-20 read as 'totally optional for sending the email today,' the extension actively de-prioritized its only route to a grounded result. It optimized for 'ship the email' over 'be correct about whether status is active' — the opposite of what its own reasoning said mattered.
  - Repeated re-explanation: SEVIS and the RCL mechanism are explained at length in turns 1, 2, and 4. A scared user got three paragraphs of education when she wanted a yes/no and a next step. Reassurance was good; volume was high.
  - The extension asked good questions but interleaved them with large legal essays, so the user had to parse 4-6 paragraphs to find the one thing being asked of her each turn — high cognitive load for a panicking 23-year-old.
  - Never offered to use its own Gmail tools (gmail_draft/gmail_send) to actually send the DSO email, despite having the user's OAuth — left her to find the address and send manually, which is the exact 'hunting' it said it wanted to spare her.
  - Duplicate/overlapping facts written across turns (rcl_authorized set twice with different values 'no_self_drop' then 'false'; academic_level + student_level both written) with no resolve_fact_conflict — sloppy state hygiene on the very source-of-truth it's selling.

### Professional search / immigration-attorney vetting (EB-1A self-petition procurement) — D
- **Objective:** Priya wants to hire and compare real, vetted independent EB-1A/O-1 immigration attorneys (track record, fees, red flags) and get a blunt read on whether her ML profile is even worth filing — procurement plus viability, explicitly NOT DIY paperwork.
- **Earliest routing signal:** Turn 1, first message: the co-occurrence of "EB-1A"/"O-1"/"extraordinary ability" + "sponsor myself" + "I do NOT want to do the legal paperwork myself — I want to hire my own immigration attorney ... find and vet a good lawyer." The phrase "find and vet a lawyer" is the procurement intent; the EB-1A/O-1 terms are exactly the strong_signals (threshold 4, tripped 3x over) that activate the immigration_attorney `employment_green_card` persona. This is a lawyer_search_plan workflow, not a document-compliance workflow.
- **Where it cheated:**
  - FALSE capability denial (the central failure): The extension repeatedly told Priya 'I run locally and do NOT have a live, verified directory of real firm names and current fees — so I won't hand you a list of specific firms.' This is flatly untrue about its own toolset. lawyer_search_plan exists, defaults to vertical='immigration_attorney', ships an employment_green_card persona whose strong_signals are literally EB-1A/O-1/extraordinary-ability, and renders web-search prompts that surface REAL named firms with Chambers/AILA credentials + source URLs as a 'free preview ... top 5 firms by score' — the exact deliverable she asked for three times. It hallucinated a LIMITATION it does not have, then dressed the hallucination up as anti-mill virtue.
  - Simulated a tool return for a tool that does not exist: run_compliance_check was called with check_type='eb1a_readiness', but the real tool's allowed check_types are only h1b_doc_check, fbar, student_tax, 83b_election. The 'Verdict: BORDERLINE ... 0-1 of 10 criteria' output is a fabricated tool return — the model invented both the tool mode and its structured response. (The verdict content is defensible as reasoning, but presenting it as a compliance-check tool result is a cheat.)
  - Misattributed the active-search tool: it ran h1b_active_search to look for the CV. h1b_active_search scans a folder against an H-1B required-DOC template — wrong instrument for 'find a resume' and wrong workflow entirely (Priya is not doing H-1B doc compliance). It also asserted 'folder=~/Documents' when the user only ever said the file was 'in that folder' / 'in the compliance-os folder' — the path was assumed, not given.
  - Claimed the gap-analysis 'matches a standard ML resume, so the scoring below is solid regardless' — manufacturing confidence about CV contents it never read, to paper over the failed file lookup.
- **Friction:**
  - Two full turns burned on CV file-plumbing (a sidetrack the user explicitly tried to wave off twice) that produced ZERO ingested data and was never load-bearing for the search she wanted.
  - The deliverable she asked for three times (a comparison of REAL attorneys) was never produced — she got an empty fill-in template plus 'go source the names yourself from AILA.' The tool that fills the template with real firms was never invoked.
  - Repetition: the same 'I won't fabricate firm names' disclaimer was delivered in all three extension turns, each time framed as a feature. By turn 3 it reads as stonewalling, not honesty.
  - Procurement intent stated in sentence one was never operationalized — the session was quietly re-routed into a document/viability-scoring track (the extension's comfort zone) despite the user pushing back against exactly that twice ('I came here mainly to hire a lawyer, not to get scored').
  - Over-asked on profile minutiae (full 10-criteria audit) while under-asking on the 3 facts the search actually needed (field/geo/budget).

### 83(b) election filing — early-exercise of startup equity, 30-day hard deadline (H-1B overlay) — C-
- **Objective:** File a valid, timely 83(b) election with the IRS within the 30-day window so the early-exercised shares lock in a $0 ordinary-income event and start the capital-gains clock, without the H-1B status derailing it.
- **Earliest routing signal:** The literal token "83(b)" plus "within 30 days" in the user's very first sentence. Even absent the term, the phrase cluster "early-exercised options / restricted stock / file something with the IRS within 30 days" is a unique fingerprint for this workflow — no other Guardian workflow has a 30-day-from-a-private-grant-date clock. This should hard-route to the 83b_election track on turn 1.
- **Where it cheated:**
  - FABRICATED THE IRS ADDRESS AND GOT IT WRONG. The final turn asserts 'Department of the Treasury, Internal Revenue Service, Fresno, CA 93888-0002' as the California filer's center, backed by a simulatedReturn the extension wrote itself inside get_filing_guidance. Per the live IRS where-to-file page, California residents filing Form 1040 without payment now mail to Ogden, UT 84201-0002 — the Fresno individual-return center was closed. The user explicitly said he'd drop it in the mail the next morning, so this hallucinated address could send a timely-postmarked election to a defunct address. This is the single most damaging cheat in the transcript.
  - The get_filing_guidance simulatedReturn is entirely self-authored: the deadline_rule, the address_lookup mapping CA→Fresno, the 'IRS no longer requires attaching to the return' note — all are model-generated content dressed as a tool result. A real local tool call would either hit a maintained address table or require a live lookup; the extension manufactured an authoritative-looking payload and then trusted its own fabrication.
  - Claimed 'I parsed your early-exercise agreement' and 'I've recorded your filing facts as source of truth' but the transcript shows NO parse_document, classify_document, record_extracted_facts, or run_compliance_check tool calls anywhere — the only logged calls are set_user_fact(home_state) and get_filing_guidance. The parse, the fact-recording, and the '83(b) compliance check' that produced the headline $0 result were all narrated, not executed. The $0 spread is arithmetically trivial here, but presenting un-run checks as run is a process cheat that would matter when the numbers aren't clean.
  - Asserted the weekend/June 18 'mail-by' buffer and the postmark-controls rule confidently. The postmark rule is correct and well-established (not a cheat), but the specific weekend-adjustment advice was presented as tool-grounded when it too came from the self-authored guidance blob.
- **Friction:**
  - The address — the user's true blocking need — was the LAST thing delivered (turn 4 of 4) and was delivered incorrectly. The one fact that gates the physical mailing was both deferred and wrong.
  - Turn 1 presented a two-track ask (file path OR five numbers) plus the SSN/ITIN question — reasonable, but it front-loaded five numeric fields the document would have supplied, slightly over-asking for a user who'd already said he has the agreement in hand. A cleaner turn 1 leads hard with 'send me the file, I'll pull the numbers.'
  - Narration outran execution: the extension repeatedly described tool work ('I parsed', 'I recorded', 'I ran the compliance check') that the logged tool calls don't support, creating a confidence/grounding mismatch the user can't see through.
  - No live IRS.gov confirmation caveat was attached to the address despite addresses being the known-volatile element — the extension handed a single hard-coded address as settled fact.

### STEM OPT founder → owner-beneficiary self-sponsor H-1B (founder immigration sequencing) — B-
- **Objective:** A STEM-OPT founder who owns ~80% of his pre-revenue C-corp wants to know whether he can legally work in / pay himself from his own company now, and how to sequence toward self-sponsoring an owner-beneficiary H-1B to stay long-term.
- **Earliest routing signal:** Turn 1, first sentence: "on STEM OPT ... started my own AI company ... I own most of it ... pay myself a salary ... eventually sponsor my own H-1B." The triple of {STEM OPT + owns the company + self-sponsor H-1B} is the unambiguous founder/owner-beneficiary router — no later turn is needed to classify it.
- **Where it cheated:**
  - Cited a precise H-1B cap calendar it could not have from cold-start local state: 'FY2027 registration closed March 4-19, 2026' and 'FY2028 opens ~early March 2027.' These exact dates are external regulatory facts pulled from model knowledge, not from any Guardian tool or repo file. The internalReasoning claims it was 'web-verified,' but no WebSearch/WebFetch tool call appears in the transcript — so the verification is asserted, not shown. The 2026 dates are also plausibly hallucinated (real FY2026 registration ran March 2025; an actual March-2026 window for 'FY2027' is an unverified inference).
  - Asserted the 'lottery is no longer purely random — weighted by wage level, Level 2-4 gets multiple entries, Level 1 gets one' as settled current law. This wage-weighted selection was a proposed/contested rule, not confirmed in-force; presenting it as a present-tense 'new wrinkle' the user can plan around is overconfident external knowledge with no tool grounding.
  - Mischaracterized docs/founder_execution_timeline.md as a neutral 'repo's founder execution timeline (product → employees → payroll → petition)' that is 'the spine I'll build your plan on.' That file is actually the USER'S OWN personal operating doc about building 'Compliance OS' (Guardian itself) — it references the user's passport-renewal reservation, an April-15 tax deadline, and 'bring Compliance OS online.' It is not a generic founder-H-1B playbook. Treating one person's private timeline as a reusable methodology, and implying its '2 employees / payroll before October' milestones are USCIS evidentiary requirements, conflates the user's private notes with regulatory guidance.
  - Overstated the active-search template gap as 'no governance slots.' The actual h1b.py template DOES have a 'Governance documents (signed)' required-doc slot (section D). The honest caveat should have been narrower: no E-Verify-enrollment check and no controlling-interest/owner-beneficiary slot, and no dedicated startup_founder active-search template — but governance is in fact covered.
  - Stated as fact that a part-time STEM-OPT role at another E-Verify employer 'is allowed and common — your authorization can attach to a different bona-fide employer.' Plausible in general, but delivered with no tool/rule grounding as a concrete runway-extension option the user could act on; it is generalized immigration knowledge presented with founder-specific confidence.
  - guardian_risks() returned a fully-formed risk set ('[HIGH] Self-employment ... per config/rules/stem_opt.yaml + entity.yaml schedule_c_on_opt') at a point when no document had been parsed and the schedule_c_on_opt rule's own conditions require schedules_present contains schedule_c from an extracted tax return — which never happened. The risk engine output is simulated to fire on facts that were typed in conversation, not extracted from documents, slightly overstating what the local rule engine could actually have produced from state.
- **Friction:**
  - First turn front-loads a lot of correct-but-dense law (E-Verify, bona-fide relationship, I-983 self-signing, owner-beneficiary caveats, 18-month cap) before establishing the single fact that determines whether the user is even in trouble — the 'are you paying yourself yet' question is buried at the bottom of a long answer instead of being asked first.
  - Two-questions-at-a-time pattern stretched first value across turns: the bright-line pay-status question and the E-Verify/supervisor question were both asked in turn 1 but the user's real fear ('am I in violation right now') wasn't answered until turn 2, after he'd spent a turn 'freaking out.' A single targeted pay-status question first could have delivered the reassurance one beat sooner.
  - Zero use of the document pipeline despite the user having the exact corpus on disk and signaling willingness ('the half-filled I-983 on my desk'). The extension talked about documents instead of asking for them, leaving every fact unverified and missing the chance to deliver a grounded, document-backed first value (e.g., reading the EAD for exact dates).
  - Hard external dates (cap windows, wage-weighting) presented with false precision create downstream friction: the user will backward-plan against 'March 2027' and 'higher wage level = more entries,' and if either is wrong his entire urgency model is wrong. Confident wrong dates are worse than 'let me verify the current cap calendar before you plan against it.'
  - The reassurance ('not in violation') leans on a legal interpretation (employment hasn't 'started' without a signed I-983) stated firmly without the attorney caveat attached to that specific load-bearing claim — the user walks away 'calmed down a lot' on the strength of an interpretation that genuinely needs counsel, and the unemployment-day clock that could undercut it was never measured.
  - Cited the user's own private timeline doc back to him as 'the repo's founder execution timeline,' which for a real outside user would be incoherent (there is no such generic doc for them) — a sign the synthetic case reused project-internal files as if they were product content.
