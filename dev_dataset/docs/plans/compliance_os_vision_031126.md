# Compliance OS for Immigrants — Product Vision & Strategy
**Date:** 2026-03-11
**Positioning:** "We are the system of record and risk engine for immigrant compliance, with humans at the advice boundary."

---

## The Buildable Company

A **continuous compliance OS for immigrants**: document system of record, deadline/risk engine, and credentialed expert routing when the user crosses into legal or tax advice territory.

**Not** "AI lawyer/CPA for immigrants." The safe product boundary is: organize, monitor, warn, educate with sources, and escalate — not "let the agent decide your case."

---

## Why This Idea Works

Immigrant compliance is genuinely multi-regime and easy to confuse:
- IRS: Form 8843 (exempt individual day exclusion), Form 3520 (foreign trusts / large foreign gifts by U.S. persons), Form 3520-A (foreign trust with U.S. owner)
- DHS/USCIS: separate timing and reporting obligations around OPT/STEM OPT, Form I-765
- Users often blend together tax-residency rules, information returns, and immigration-status rules even though they come from different systems

---

## Adjacent Market Proof

People and institutions already pay for slices of this problem:

| Segment | Players |
|---------|---------|
| Consumer immigration | Boundless, SimpleCitizen |
| Nonresident/intl student tax | Sprintax, Glacier |
| Law firm/nonprofit workflow | Docketwise, eimmigration, INSZoom, LawLogix |
| University/student enablement | Interstride |
| Corporate immigration/mobility | Envoy, Fragomen, BAL, Deel, Gale |

**What's underbuilt:** a user-centric layer that keeps one person's status, documents, dates, and expert escalation synchronized over time.

---

## Core Product (V1)

1. **Document vault + timeline** — knows what the user has, what is missing, what expires, what changed
2. **Deterministic compliance engine** — dates, thresholds, event triggers (rules/code, not LLM)
3. **Risk detector** — "this change may affect your status/tax filing; here is why; here are the sources"
4. **Credentialed escalation** — route to the right lawyer/EA/CPA when advice is needed
5. **Post-consult action layer** — turns advice into reminders, checklists, tracked obligations

**The moat is not workflow automation. The moat is the regulatory state model** — a domain graph of visa status, entry/exit history, school/employment events, tax-residency logic, document dependencies, filing windows, and escalation rules.

---

## Unauthorized Practice Risk (The Biggest Failure Mode)

- **Immigration:** DOJ warns only licensed attorneys and accredited representatives can provide immigration legal advice. Notarios and immigration consultants cannot.
- **California lawyer referral:** State Bar certification required. Certified LRSs must meet minimum standards; referred lawyers must carry malpractice insurance.
- **Tax:** IRS says only attorneys, CPAs, and enrolled agents have unlimited practice rights. IRS maintains searchable directory of credentialed preparers.
- **Expert sourcing:** Don't start with a free-form marketplace. Build structured triage + verified routing. Use objective signals (bar status, jurisdiction, practice area, languages). Note: AILA's lawyer search explicitly says it is not a lawyer referral service and may not be used for commercial/promotional purposes.

---

## Agentic Architecture Principles

- **Keep the model off the critical path for legal conclusions**
- Use rules/code for deterministic obligations
- Use retrieval from official sources for explanations
- Use human review for anything high-risk
- Similar-case search: useful for generating missing-fact questions or surfacing adjacent risks — not for promising approval odds
- **Governance:** NIST AI Risk Management Framework and Generative AI Profile

---

## Meeting Recording

Don't make it a core assumption. Lawyers' resistance is rational:
- California guidance: lawyers must not input confidential client information into a generative-AI system lacking adequate confidentiality/security protections
- ABA Formal Opinion 512: duties of competence, confidentiality, communication, supervision when lawyers use AI
- **Better design:** recording optional and consent-based with strong controls; default workflow works from user-uploaded documents and structured post-call recap

---

## Privacy & Trust Architecture

Baseline for a small startup:
- Collect minimum data necessary
- Explicit: do not train models on customer documents
- Encrypt in transit and at rest
- MFA and role-based access
- Audit logs
- User export/delete controls
- Published retention windows
- Breach playbook
- **References:** FTC "Start with Security", "Protecting Personal Information", NIST small-business security guidance
- **Enterprise:** SOC 2 becomes a trust signal for institutional buyers

---

## Legal Compliance Layers

**Layer 1 — General consumer privacy/security:**
- FTC deception/unfairness risk
- State breach notification laws (all 50 states)
- CCPA/CPRA if thresholds met (2025 inflation-adjusted revenue: $20,767,500, or 100K+ CA residents, or 50%+ revenue from selling/sharing PI)

**Layer 2 — Tax-prep specific (if functioning as tax-prep provider or service provider to tax professionals):**
- GLBA Safeguards Rule
- IRS Publication 4557
- IRC Section 7216 (disclosure/use of tax return information by preparers)

---

## GTM Strategy

**First wedge:** F-1 / OPT / STEM OPT / first-job immigrants who need ongoing immigration + tax-compliance tracking and don't know when to escalate to a professional.

Why this segment:
- Repeated deadlines
- Recurring document needs
- Clear anxiety
- Relatively concentrated distribution
- Price-sensitive (don't rely on pure B2C subscription alone)

**B2B2C path:** Institutions already buy adjacent tools:
- Berkeley and UC Santa Cruz sponsor Glacier Tax Prep for international students/scholars
- Stanford and UCLA provide Sprintax access
- Many schools provide Interstride for immigration/career support

Suggests plausible distribution through universities, international offices, or employers.

---

## Three Promises

1. **Never miss a deadline**
2. **Never lose the document trail**
3. **Never talk to the wrong expert**

---

## Expansion Path

1. **V1:** Individual F-1/OPT/STEM-to-early-career compliance OS
2. **V2:** Employer-side immigration compliance
3. **V3:** Broader cross-border corporate compliance (Chinese firms entering U.S.)

Enterprise cross-border is a different buyer, different sales motion, broader surface area — treat as later company stage.

References for V3 adjacency: SelectUSA investor guide (business structure/taxes as core early issues), CFIUS reviews for foreign investment/real-estate transactions, existence of Envoy/Fragomen/BAL/Deel shows meaningful enterprise spend.

---

## Differentiation from Generic Agent Builders (BubbleLab etc.)

Generic workflow/agent builders can automate tasks but don't inherently provide:
- Regulatory correctness
- Privilege boundaries
- Source accountability
- Trustworthy expert routing

**Core asset:** domain graph of visa status, entry/exit history, school/employment events, tax-residency logic, document dependencies, filing windows, escalation rules — not just automations.

**Gale as reference:** explicitly positions itself as software plus independent lawyers, states it is not a law firm, legal fees paid separately, communications not covered by attorney-client privilege. That boundary-setting is part of product design, not just legal fine print.

---

## This Repo as Prototype

This accounting repository serves as a real-world prototype for the compliance OS architecture. It already contains:
- Document vault (PDFs, tax forms, immigration records, bank statements)
- Deadline tracking (concerns/deadlines.txt)
- Multi-regime compliance issues (concerns/tax_and_compliance_issues_021226.txt)
- Expert interaction records (lawyer consultations, CPA meetings)
- Action item tracking and status management

The goal is to extract the architecture patterns from this prototype into a production application.
