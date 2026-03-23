"""Seeded MVP workspace data for the first runnable product-feel prototype."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from itertools import count

from compliance_os.compliance.schemas import Deadline


REFERENCE_DATE = date(2026, 3, 19)
UNRESOLVED_ANSWERS = {"Need to confirm", "Need to collect", "Unknown"}


def _deadline(
    deadline_id: str,
    title: str,
    due_date: date,
    category: str,
    concern_id: str,
    action: str,
    auto_extend_to: date | None = None,
) -> dict:
    item = Deadline(
        id=deadline_id,
        title=title,
        due_date=due_date,
        category=category,
        action=action,
        auto_extend_to=auto_extend_to,
    )
    item.status = item.compute_status(REFERENCE_DATE)
    return {
        "id": item.id,
        "title": item.title,
        "due_date": item.due_date.isoformat(),
        "status": item.status.value,
        "category": item.category,
        "action": item.action,
        "concern_id": concern_id,
    }


INITIAL_STATE = {
    "workspace": {
        "id": "founder-workspace",
        "title": "Founder Compliance Workspace",
        "subtitle": "Documents, concerns, Gmail, deadlines, and action drafts in one place.",
        "mode_label": "Claude co-work preview",
        "as_of": REFERENCE_DATE.isoformat(),
    },
    "quick_prompts": [
        "What am I missing for the 1040-NR correction?",
        "Check whether any Gmail thread changes my H-1B timeline.",
        "Draft a follow-up to Fan Chen.",
        "Show me every document related to Form 3520.",
    ],
    "discovery_sessions": [
        {
            "id": "discovery-1040nr",
            "concern_id": "concern-1040nr",
            "case_type": "Tax compliance review",
            "current_stage": "Post-filing review before amendment planning",
            "urgency_label": "Need clarity before the 2025 filing deadline",
            "professional_status": "No tax professional is retained yet; expert routing is still open.",
            "current_tools": "Prior self-filed returns, Gmail threads, and the accounting notes repository.",
            "initial_understanding": "The likely issue is that 2023 and 2024 may have been filed as Form 1040 during a period that still qualified for nonresident treatment under the F-1 exempt-individual window. Before amendment planning, the system needs filing history, 8843 history, and state-return context.",
            "watch_outs": [
                "Do not start amendments until the residency position is confirmed.",
                "The federal answer changes California and foreign-reporting downstream work.",
            ],
            "questions": [
                {
                    "id": "dq-1040-entry",
                    "label": "First U.S. entry under F-1",
                    "prompt": "When did you first enter the U.S. under F-1 status?",
                    "help_text": "This anchors the exempt-individual window for the tax residency analysis.",
                    "options": ["Oct 2023", "2024", "Need to confirm"],
                    "answer": "Oct 2023",
                    "status": "captured",
                    "follow_up_item": "Confirm the first U.S. entry date from passport stamps or the I-94 history.",
                },
                {
                    "id": "dq-1040-8843",
                    "label": "Form 8843 filing history",
                    "prompt": "Did you file Form 8843 for both 2023 and 2024?",
                    "help_text": "This is one of the first facts an expert will ask for in the residency correction analysis.",
                    "options": ["Yes, both years", "Only one year", "Need to confirm"],
                    "answer": "Need to confirm",
                    "status": "needs_follow_up",
                    "follow_up_item": "Locate or reconstruct the Form 8843 filing history before amendment planning.",
                },
                {
                    "id": "dq-1040-preparer",
                    "label": "Original filing workflow",
                    "prompt": "How were the original Form 1040 returns prepared?",
                    "help_text": "This affects how much reconstruction work is needed and where the filing assumptions came from.",
                    "options": ["TurboTax / self-filed", "CPA prepared", "Need to confirm"],
                    "answer": "TurboTax / self-filed",
                    "status": "captured",
                    "follow_up_item": "Confirm which software or preparer produced the original returns.",
                },
                {
                    "id": "dq-1040-state",
                    "label": "California return status",
                    "prompt": "Was a California state return filed for 2024?",
                    "help_text": "Federal residency treatment can change the state filing correction plan.",
                    "options": ["Yes", "No", "Need to confirm"],
                    "answer": "Need to confirm",
                    "status": "needs_follow_up",
                    "follow_up_item": "Confirm the California filing status before building the correction plan.",
                },
            ],
        },
        {
            "id": "discovery-3520",
            "concern_id": "concern-3520",
            "case_type": "Foreign gift reporting review",
            "current_stage": "Pre-filing threshold and donor analysis",
            "urgency_label": "Need evidence packaging before the April filing window",
            "professional_status": "Still self-reviewing before expert confirmation.",
            "current_tools": "Bank transfer records, transaction analysis notes, and outreach drafts.",
            "initial_understanding": "The key question is whether repeated family wire transfers create a Form 3520 filing obligation, especially if related-party aggregation applies. The system needs a clean ledger, donor identities, and a confirmed reporting theory before filing.",
            "watch_outs": [
                "Do not rely on general student-exemption logic for gift reporting.",
                "The penalty exposure is high if the threshold analysis is wrong.",
            ],
            "questions": [
                {
                    "id": "dq-3520-ledger",
                    "label": "Wire ledger completeness",
                    "prompt": "Is there already a clean ledger of all 2025 family wire receipts?",
                    "help_text": "A by-date ledger is the minimum evidence layer for threshold review.",
                    "options": ["Yes, complete", "Partial only", "Need to collect"],
                    "answer": "Partial only",
                    "status": "needs_follow_up",
                    "follow_up_item": "Finish the 2025 family wire ledger with dates, amounts, and sender names.",
                },
                {
                    "id": "dq-3520-donors",
                    "label": "Donor identity evidence",
                    "prompt": "Do you have donor names and relationship details tied to each transfer?",
                    "help_text": "This matters for related-party aggregation and support if the form must be filed.",
                    "options": ["Yes", "Partially", "Need to collect"],
                    "answer": "Partially",
                    "status": "needs_follow_up",
                    "follow_up_item": "Document donor identities and family relationships for each transfer.",
                },
                {
                    "id": "dq-3520-related-party",
                    "label": "Related-party aggregation theory",
                    "prompt": "Has anyone confirmed whether related-party aggregation is the right interpretation for this pattern?",
                    "help_text": "This is one of the highest-value expert questions in the review.",
                    "options": ["Yes, confirmed", "No, still open", "Need to confirm"],
                    "answer": "No, still open",
                    "status": "needs_follow_up",
                    "follow_up_item": "Get one professional answer on related-party aggregation before filing.",
                },
                {
                    "id": "dq-3520-bank-records",
                    "label": "Bank statement backup",
                    "prompt": "Are the matching bank statements ready to support the transfer history?",
                    "help_text": "The ledger should tie back to statements so the case record is audit-ready.",
                    "options": ["Yes", "Partially", "Need to collect"],
                    "answer": "Partially",
                    "status": "needs_follow_up",
                    "follow_up_item": "Collect matching bank statements for the family wire receipts.",
                },
            ],
        },
        {
            "id": "discovery-sevis",
            "concern_id": "concern-sevis",
            "case_type": "Immigration timeline review",
            "current_stage": "Pre-petition record cleanup",
            "urgency_label": "Needs resolution before H-1B petition prep",
            "professional_status": "Counsel has answered some questions, but the evidence package is incomplete.",
            "current_tools": "SEVIS timeline notes, paystubs, employer correction evidence, Gmail correspondence.",
            "initial_understanding": "The open question is whether the SEVIS employment history and supporting records are clean enough for later petition stages. The product should help assemble the exact employer timeline and flag any unsupported gaps before counsel review.",
            "watch_outs": [
                "Do not rely on memory for employment dates when documentary evidence exists.",
                "This issue is less about theory and more about evidence completeness.",
            ],
            "questions": [
                {
                    "id": "dq-sevis-timeline",
                    "label": "Employer timeline completeness",
                    "prompt": "Do you already have every OPT and STEM OPT employer with start and end dates in one timeline?",
                    "help_text": "This is the core timeline artifact for the SEVIS cleanup review.",
                    "options": ["Yes", "Partially", "Need to collect"],
                    "answer": "Partially",
                    "status": "needs_follow_up",
                    "follow_up_item": "Build one consolidated OPT/STEM OPT employer timeline with start and end dates.",
                },
                {
                    "id": "dq-sevis-evidence",
                    "label": "Correction evidence package",
                    "prompt": "Are the employer correction letter, paystubs, and SEVIS notes linked together already?",
                    "help_text": "The evidence package should be reusable for any future immigration review.",
                    "options": ["Yes", "Partially", "Need to collect"],
                    "answer": "Partially",
                    "status": "needs_follow_up",
                    "follow_up_item": "Link employer correction evidence, paystubs, and SEVIS notes into one packet.",
                },
                {
                    "id": "dq-sevis-counsel",
                    "label": "Counsel answer on cleanup timing",
                    "prompt": "Has counsel already said whether cleanup must happen before the petition stage?",
                    "help_text": "This determines whether the issue is immediate or just something to preserve.",
                    "options": ["Yes", "No", "Need to confirm"],
                    "answer": "Yes",
                    "status": "captured",
                    "follow_up_item": "Get a direct counsel answer on whether cleanup is required before petition prep.",
                },
            ],
        },
        {
            "id": "discovery-passport",
            "concern_id": "concern-passport",
            "case_type": "Passport dependency review",
            "current_stage": "Pre-petition readiness",
            "urgency_label": "Renewal timing can block the later petition package",
            "professional_status": "Counsel gave a directional answer; execution is still pending.",
            "current_tools": "Passport expiry date, consulate planning notes, counsel email thread.",
            "initial_understanding": "This is not a theory-heavy issue. The main job is to avoid a preventable filing blocker by starting renewal early enough and preserving both old and new passport copies for the petition record.",
            "watch_outs": [
                "Registration may be fine now, but the full petition needs a valid passport.",
            ],
            "questions": [
                {
                    "id": "dq-passport-started",
                    "label": "Renewal process started",
                    "prompt": "Has the passport renewal process already been started?",
                    "help_text": "This is the highest-value execution fact for this concern.",
                    "options": ["Yes", "No", "Need to confirm"],
                    "answer": "No",
                    "status": "needs_follow_up",
                    "follow_up_item": "Start the passport renewal process before the petition window tightens.",
                },
                {
                    "id": "dq-passport-copies",
                    "label": "Old and new passport copies",
                    "prompt": "Do you have a plan to keep copies of both the current and renewed passports?",
                    "help_text": "The petition record should preserve both versions once the renewal is complete.",
                    "options": ["Yes", "No", "Need to confirm"],
                    "answer": "Yes",
                    "status": "captured",
                    "follow_up_item": "Prepare to preserve both old and new passport copies for the petition packet.",
                },
            ],
        },
    ],
    "upload_requests": [
        {
            "id": "upload-2023-return",
            "concern_id": "concern-1040nr",
            "title": "2023 filed federal return package",
            "description": "Needed to compare the original filing position against the possible 1040-NR amendment theory.",
            "priority": "required",
            "status": "missing",
            "target_folder": "Tax filings",
            "accepted_types": ["PDF", "scan"],
            "document_seed": {
                "id": "doc-2023-return-upload",
                "title": "2023 filed federal return package",
                "type": "tax-return",
                "source_path": "Data Room / Tax filings / 2023_federal_return.pdf",
                "excerpt": "Original 2023 filed Form 1040 package uploaded for amendment comparison and residency review.",
                "room_folder": "Tax filings",
                "ingestion_status": "ready",
            },
        },
        {
            "id": "upload-2024-return",
            "concern_id": "concern-1040nr",
            "title": "2024 filed federal return package",
            "description": "Needed to confirm whether the same residency assumption flowed into the next filing year.",
            "priority": "required",
            "status": "missing",
            "target_folder": "Tax filings",
            "accepted_types": ["PDF", "scan"],
            "document_seed": {
                "id": "doc-2024-return-upload",
                "title": "2024 filed federal return package",
                "type": "tax-return",
                "source_path": "Data Room / Tax filings / 2024_federal_return.pdf",
                "excerpt": "Original 2024 filed return uploaded for consistency review against the possible 1040-NR correction plan.",
                "room_folder": "Tax filings",
                "ingestion_status": "ready",
            },
        },
        {
            "id": "upload-8843-history",
            "concern_id": "concern-1040nr",
            "title": "Form 8843 filing history",
            "description": "Needed to confirm whether 8843 was filed and in which years, which affects the residency review narrative.",
            "priority": "required",
            "status": "missing",
            "target_folder": "Tax filings",
            "accepted_types": ["PDF", "scan"],
            "document_seed": {
                "id": "doc-8843-history-upload",
                "title": "Form 8843 filing history",
                "type": "supporting-form",
                "source_path": "Data Room / Tax filings / 8843_history.pdf",
                "excerpt": "Form 8843 filings and proof of submission uploaded to support the residency correction analysis.",
                "room_folder": "Tax filings",
                "ingestion_status": "ready",
            },
        },
        {
            "id": "upload-wire-ledger",
            "concern_id": "concern-3520",
            "title": "2025 family wire ledger",
            "description": "A dated ledger of all family wire receipts with sender names and posted amounts.",
            "priority": "required",
            "status": "missing",
            "target_folder": "Financial evidence",
            "accepted_types": ["CSV", "XLSX", "PDF"],
            "document_seed": {
                "id": "doc-wire-ledger-upload",
                "title": "2025 family wire ledger",
                "type": "financial-ledger",
                "source_path": "Data Room / Financial evidence / 2025_family_wire_ledger.xlsx",
                "excerpt": "Wire ledger uploaded for Form 3520 threshold review and related-party aggregation analysis.",
                "room_folder": "Financial evidence",
                "ingestion_status": "ready",
            },
        },
        {
            "id": "upload-donor-sheet",
            "concern_id": "concern-3520",
            "title": "Donor relationship sheet",
            "description": "Maps each sender to a relationship and donor identity for aggregation analysis.",
            "priority": "required",
            "status": "missing",
            "target_folder": "Financial evidence",
            "accepted_types": ["PDF", "XLSX"],
            "document_seed": {
                "id": "doc-donor-sheet-upload",
                "title": "Donor relationship sheet",
                "type": "supporting-evidence",
                "source_path": "Data Room / Financial evidence / donor_relationship_sheet.xlsx",
                "excerpt": "Donor names, family relationships, and transfer groupings uploaded for the Form 3520 case record.",
                "room_folder": "Financial evidence",
                "ingestion_status": "ready",
            },
        },
        {
            "id": "upload-sevis-timeline",
            "concern_id": "concern-sevis",
            "title": "OPT/STEM OPT employer timeline",
            "description": "One consolidated employer timeline with start and end dates for each period.",
            "priority": "required",
            "status": "missing",
            "target_folder": "Immigration timeline",
            "accepted_types": ["PDF", "XLSX"],
            "document_seed": {
                "id": "doc-sevis-timeline-upload",
                "title": "OPT/STEM OPT employer timeline",
                "type": "immigration-timeline",
                "source_path": "Data Room / Immigration timeline / opt_stem_employer_timeline.xlsx",
                "excerpt": "Consolidated employer timeline uploaded to support the SEVIS cleanup review.",
                "room_folder": "Immigration timeline",
                "ingestion_status": "ready",
            },
        },
        {
            "id": "upload-passport-copy",
            "concern_id": "concern-passport",
            "title": "Current passport scan",
            "description": "Current passport scan for renewal tracking and future petition packaging.",
            "priority": "required",
            "status": "missing",
            "target_folder": "Identity and travel",
            "accepted_types": ["PDF", "image"],
            "document_seed": {
                "id": "doc-passport-copy-upload",
                "title": "Current passport scan",
                "type": "identity-document",
                "source_path": "Data Room / Identity and travel / current_passport_scan.pdf",
                "excerpt": "Current passport scan uploaded to track renewal timing and preserve identity evidence.",
                "room_folder": "Identity and travel",
                "ingestion_status": "ready",
            },
        },
    ],
    "ingestion_jobs": [
        {
            "id": "job-tax-readme",
            "concern_id": "concern-1040nr",
            "title": "2025 tax document tracker",
            "status": "ready",
            "progress": 100,
            "detail": "Residency, state filing, and W-2 references extracted into the structured case record.",
        },
        {
            "id": "job-tax-register",
            "concern_id": "concern-1040nr",
            "title": "Tax and compliance issues register",
            "status": "needs_review",
            "progress": 100,
            "detail": "Cross-document fields were extracted, but Form 8843 history is still unresolved.",
        },
        {
            "id": "job-wire-analysis",
            "concern_id": "concern-3520",
            "title": "International wire and account analysis",
            "status": "ready",
            "progress": 100,
            "detail": "Transfer dates, amounts, and open aggregation questions were parsed into the case record.",
        },
        {
            "id": "job-sevis-analysis",
            "concern_id": "concern-sevis",
            "title": "SEVIS employment record analysis",
            "status": "processing",
            "progress": 72,
            "detail": "Matching employer names, timeline edges, and evidence references across the immigration packet.",
        },
    ],
    "documents": [
        {
            "id": "doc-tax-readme",
            "title": "2025 tax document tracker",
            "type": "tax",
            "source_path": "/Users/lichenyu/accounting/tax/2025/README.txt",
            "excerpt": "Residency determination needed: 1040 vs 1040-NR; NY and CA state filing implications; Claudius W-2 retrieval and employer correction context.",
            "room_folder": "Tax filings",
            "ingestion_status": "ready",
            "uploaded_at": "2026-03-12T09:20:00-07:00",
            "linked_concern_ids": ["concern-1040nr", "concern-3520", "concern-w2"],
        },
        {
            "id": "doc-wolf-group",
            "title": "Wolf Group consultation request",
            "type": "expert-routing",
            "source_path": "/Users/lichenyu/accounting/outgoing/wolf_group/consultation_request_draft.txt",
            "excerpt": "Summarizes the full multi-year amendment issue: 1040 to 1040-NR, Form 5472/pro forma 1120, foreign gifts, foreign accounts, and state return questions.",
            "room_folder": "Professional correspondence",
            "ingestion_status": "ready",
            "uploaded_at": "2026-03-13T15:10:00-07:00",
            "linked_concern_ids": ["concern-1040nr", "concern-fanchen"],
        },
        {
            "id": "doc-tax-register",
            "title": "Tax and compliance issues register",
            "type": "risk-register",
            "source_path": "/Users/lichenyu/accounting/concerns/tax_and_compliance_issues_021226.txt",
            "excerpt": "Tracks the cascade effect of filing as Form 1040, Form 3520 threshold analysis, possible FBAR/FATCA implications, and open lawyer questions.",
            "room_folder": "Tax filings",
            "ingestion_status": "needs_review",
            "uploaded_at": "2026-03-12T12:10:00-07:00",
            "linked_concern_ids": ["concern-1040nr", "concern-3520"],
        },
        {
            "id": "doc-sevis-analysis",
            "title": "SEVIS employment record analysis",
            "type": "immigration",
            "source_path": "/Users/lichenyu/accounting/outgoing/columbia_isso/sevis_employment_analysis_030426.txt",
            "excerpt": "Maps OPT/STEM OPT/CPT periods, unemployment limits, open-ended SEVIS records, and a potential unauthorized-employment concern that needed documentary cleanup.",
            "room_folder": "Immigration timeline",
            "ingestion_status": "processing",
            "uploaded_at": "2026-03-04T10:00:00-07:00",
            "linked_concern_ids": ["concern-sevis", "concern-passport"],
        },
        {
            "id": "doc-cindy-response",
            "title": "Cindy Chen CPT + passport response",
            "type": "legal-correspondence",
            "source_path": "/Users/lichenyu/accounting/outgoing/mt_law/cindy_cpt_passport_response_031426.txt",
            "excerpt": "Confirms passport renewal should happen sooner rather than later and that CPT at Yangtze depends on school rules for self-employment and unpaid positions.",
            "room_folder": "Professional correspondence",
            "ingestion_status": "ready",
            "uploaded_at": "2026-03-14T16:30:00-07:00",
            "linked_concern_ids": ["concern-sevis", "concern-passport"],
        },
        {
            "id": "doc-wire-analysis",
            "title": "International wire and account analysis",
            "type": "financial",
            "source_path": "/Users/lichenyu/accounting/reports/Non_Zelle_Unmatched.txt",
            "excerpt": "Shows 7 international family wires, related-party gift concerns, business vs personal cash movements, and unresolved transfer destinations.",
            "room_folder": "Financial evidence",
            "ingestion_status": "ready",
            "uploaded_at": "2026-03-10T08:45:00-07:00",
            "linked_concern_ids": ["concern-3520"],
        },
    ],
    "threads": [
        {
            "id": "thread-fanchen",
            "subject": "Follow-up on discovery meeting request",
            "counterpart": "Fan Chen / The Wolf Group",
            "last_message_at": "2026-03-18T20:14:00-07:00",
            "unread": False,
            "linked_concern_ids": ["concern-fanchen", "concern-1040nr"],
            "snippet": "Direct follow-up sent to fanchen@thewolfgroup.com asking to schedule a discovery meeting.",
            "messages": [
                {
                    "direction": "outbound",
                    "from": "fretin13@gmail.com",
                    "to": "fanchen@thewolfgroup.com",
                    "sent_at": "2026-03-13T15:04:52-07:00",
                    "body": "Sent background summary before the Mar 13 discovery meeting, including 1040-NR correction, Form 5472, foreign gifts, foreign accounts, and California return issues.",
                },
                {
                    "direction": "outbound",
                    "from": "fretin13@gmail.com",
                    "to": "fanchen@thewolfgroup.com",
                    "sent_at": "2026-03-18T20:14:00-07:00",
                    "body": "Followed up directly to request availability for a discovery meeting and reaffirmed interest in working with the firm.",
                },
            ],
        },
        {
            "id": "thread-cindy",
            "subject": "CPT Employment Timing Question — Yangtze Capital / H-1B Strategy",
            "counterpart": "Cindy Chen / MT Law",
            "last_message_at": "2026-03-14T16:18:31-04:00",
            "unread": True,
            "linked_concern_ids": ["concern-sevis", "concern-passport"],
            "snippet": "Cindy said Yangtze CPT could help if school rules allow it; passport should be renewed sooner rather than later.",
            "messages": [
                {
                    "direction": "outbound",
                    "from": "fretin13@gmail.com",
                    "to": "cindy@mtlawllc.com",
                    "sent_at": "2026-03-13T14:51:01-07:00",
                    "body": "Asked whether starting CPT at Yangtze helps establish a bona fide employment relationship and whether self-petitioning or unpaid work creates issues.",
                },
                {
                    "direction": "outbound",
                    "from": "fretin13@gmail.com",
                    "to": "cindy@mtlawllc.com",
                    "sent_at": "2026-03-13T14:57:07-07:00",
                    "body": "Asked whether the passport can be sent for renewal before the H-1B full petition window.",
                },
                {
                    "direction": "inbound",
                    "from": "cindy@mtlawllc.com",
                    "to": "fretin13@gmail.com",
                    "sent_at": "2026-03-14T16:18:31-04:00",
                    "body": "Yangtze CPT may help but only if the school allows self-employment or unpaid CPT. Passport should be renewed sooner rather than later; current passport is fine for registration but a valid passport is needed for the full petition.",
                },
            ],
        },
        {
            "id": "thread-w2",
            "subject": "2025 W-2 Request — Claudius Legal Intelligence",
            "counterpart": "Joe Avery / Accounting Solutions ENC",
            "last_message_at": "2026-03-02T11:32:00-08:00",
            "unread": False,
            "linked_concern_ids": ["concern-w2"],
            "snippet": "The W-2 was eventually delivered by the accountant after the original employer address bounced and the old mailing address caused issues.",
            "messages": [
                {
                    "direction": "outbound",
                    "from": "fretin13@gmail.com",
                    "to": "jxa1557@miami.edu",
                    "sent_at": "2026-02-27T09:14:00-08:00",
                    "body": "Requested the 2025 W-2 for Claudius Legal Intelligence.",
                },
                {
                    "direction": "inbound",
                    "from": "josephjavery1@gmail.com",
                    "to": "fretin13@gmail.com",
                    "sent_at": "2026-02-27T15:42:00-08:00",
                    "body": "Replied from a working Gmail address, noted the accountant should have sent the form in January, and asked for the current mailing address.",
                },
                {
                    "direction": "inbound",
                    "from": "caitlin@accountingsolutionsenc.com",
                    "to": "fretin13@gmail.com",
                    "sent_at": "2026-03-02T11:32:00-08:00",
                    "body": "Sent the password-protected W-2 PDF attachment.",
                },
            ],
        },
    ],
    "concerns": [
        {
            "id": "concern-1040nr",
            "title": "1040 vs 1040-NR correction stack",
            "category": "tax",
            "status": "active",
            "priority": "critical",
            "summary": "Prior returns were filed as Form 1040, but the working hypothesis is that they should have been 1040-NR during the F-1 exempt-individual window. This changes which international forms matter and whether 2023 and 2024 need amendments.",
            "why_now": "This is the foundational issue. It changes treatment of worldwide income, foreign accounts, gifts, and the 2025 filing plan.",
            "next_steps": [
                "Collect the 2023 and 2024 filed returns plus any Form 8843 history.",
                "Get one tax professional to confirm the correct residency position before amending anything else.",
                "Prepare an amendment packet outline for 2023, 2024, and the 2025 filing plan.",
            ],
            "linked_document_ids": ["doc-tax-readme", "doc-wolf-group", "doc-tax-register"],
            "linked_thread_ids": ["thread-fanchen"],
            "tags": ["1040", "1040-NR", "8843", "amendment"],
            "default_prompt": "What am I missing for the 1040-NR correction?",
            "draft_template": {
                "to": "fanchen@thewolfgroup.com",
                "subject": "Follow-up on discovery meeting request",
                "body": "Dear Fan Chen,\n\nI wanted to follow up on my request for a discovery meeting regarding my 1040 to 1040-NR corrections, 2025 filing strategy, and related international compliance issues. If you have availability this week or next, I would be grateful to schedule a time.\n\nBest regards,\nChenyu Li\n(929) 538-8280",
            },
        },
        {
            "id": "concern-3520",
            "title": "Form 3520 foreign gift threshold",
            "category": "tax",
            "status": "urgent",
            "priority": "critical",
            "summary": "The gift-reporting question is not theoretical. There are repeated family wires from China, possible related-party aggregation, and a near-miss caused by blending student exemption logic with gift-reporting logic.",
            "why_now": "The 2025 reporting deadline is close, and the penalty risk for missing Form 3520 is severe if the filing is required.",
            "next_steps": [
                "Freeze a clean ledger of all family wire receipts by posting date and sender.",
                "Resolve whether the related-party aggregation rule applies to the 2025 pattern.",
                "Prepare donor details and backup documentation in case the form must be filed.",
            ],
            "linked_document_ids": ["doc-tax-readme", "doc-tax-register", "doc-wire-analysis"],
            "linked_thread_ids": [],
            "tags": ["3520", "foreign gifts", "wires", "family transfers"],
            "default_prompt": "Show me every document related to Form 3520.",
            "draft_template": {
                "to": "fanchen@thewolfgroup.com",
                "subject": "Question on Form 3520 related-party gift analysis",
                "body": "Dear Fan Chen,\n\nI would like to make sure my 2025 foreign gift analysis is framed correctly before filing season moves further. I have a set of family wire transfers from China that may require related-party aggregation. If helpful, I can send a ledger with dates, sender names, and posting amounts in advance of a discovery call.\n\nBest regards,\nChenyu Li",
            },
        },
        {
            "id": "concern-sevis",
            "title": "SEVIS cleanup before H-1B filing",
            "category": "immigration",
            "status": "active",
            "priority": "high",
            "summary": "The SEVIS record contains open-ended employer entries from OPT and STEM OPT, plus a timeline that needed reconciliation against paystubs and later CPT dates. This is exactly the kind of issue that should be discovered from evidence, not memory.",
            "why_now": "Loose SEVIS entries and mismatched employment dates can complicate future H-1B filings or any later immigration review.",
            "next_steps": [
                "Identify every employer entry that should have an end date in SEVIS.",
                "Preserve the employer correction evidence for the paystub timing issue.",
                "Ask counsel whether any cleanup should happen before the full petition.",
            ],
            "linked_document_ids": ["doc-sevis-analysis", "doc-cindy-response"],
            "linked_thread_ids": ["thread-cindy"],
            "tags": ["SEVIS", "OPT", "STEM OPT", "CPT", "H-1B"],
            "default_prompt": "Check whether any Gmail thread changes my H-1B timeline.",
            "draft_template": {
                "to": "ajay@h1b1.com",
                "subject": "Follow-up on SEVIS employment end dates before H-1B filing",
                "body": "Hi Ajay,\n\nI wanted to follow up on my question about open-ended employer entries in my SEVIS record from the OPT and STEM OPT periods. Before the H-1B petition stage, do you recommend cleaning those end dates up, or can they stay as-is without creating downstream issues?\n\nThank you,\nChenyu Li",
            },
        },
        {
            "id": "concern-passport",
            "title": "Passport renewal before H-1B petition",
            "category": "immigration",
            "status": "watch",
            "priority": "high",
            "summary": "The current passport expires on June 30, 2026. Counsel said the registration is fine, but the full petition requires a valid passport and the renewal should happen sooner rather than later.",
            "why_now": "This is a deadline-sensitive dependency that can block later petition work if it slips.",
            "next_steps": [
                "Start the renewal process with the Chinese consulate.",
                "Keep copies of both old and new passports ready for the petition packet.",
                "Track the expected completion date against the H-1B filing window.",
            ],
            "linked_document_ids": ["doc-cindy-response", "doc-sevis-analysis"],
            "linked_thread_ids": ["thread-cindy"],
            "tags": ["passport", "H-1B", "petition"],
            "default_prompt": "What is the immediate action for the passport risk?",
            "draft_template": {
                "to": "cindy@mtlawllc.com",
                "subject": "Passport renewal update for H-1B petition planning",
                "body": "Hi Cindy,\n\nI am starting the passport renewal process now so I can keep a valid passport through the H-1B petition window. Once I receive the renewed passport, I will send both old and new copies for the petition record.\n\nBest,\nChenyu",
            },
        },
        {
            "id": "concern-fanchen",
            "title": "Tax expert routing and follow-up",
            "category": "expert-routing",
            "status": "waiting",
            "priority": "medium",
            "summary": "Multiple firms were evaluated, but the key problem is still expert quality and routing transparency. The system should help track who was contacted, what structure they operate under, and which follow-up is next.",
            "why_now": "Without a clearly matched expert, the broader amendment and filing strategy stays blocked.",
            "next_steps": [
                "Wait for Fan Chen / Wolf Group response to the direct follow-up.",
                "If no reply arrives soon, send a second follow-up or move to the next vetted tax contact.",
                "Keep a clean routing log with who was contacted, the case fit, and fee signals.",
            ],
            "linked_document_ids": ["doc-wolf-group"],
            "linked_thread_ids": ["thread-fanchen"],
            "tags": ["expert-routing", "CPA", "discovery-call"],
            "default_prompt": "Draft a follow-up to Fan Chen.",
            "draft_template": {
                "to": "fanchen@thewolfgroup.com",
                "subject": "Following up on international tax discovery meeting",
                "body": "Dear Fan Chen,\n\nI wanted to follow up once more regarding a discovery meeting for my international tax matter. I remain interested in working with your firm and would appreciate any availability you may have.\n\nBest regards,\nChenyu Li",
            },
        },
        {
            "id": "concern-w2",
            "title": "Document retrieval and employer follow-up",
            "category": "operations",
            "status": "resolved",
            "priority": "medium",
            "summary": "The Claudius W-2 issue shows why compliance work needs operational memory: wrong address, bounced email, accountant handoff, password-protected attachment, and paystub cross-checking.",
            "why_now": "This concern is mostly resolved, but it is a strong template for the product's document and inbox workflow.",
            "next_steps": [
                "Preserve the working Joe Avery Gmail address.",
                "Link the W-2 to the tax workspace and address correction note.",
                "Reuse this workflow pattern for future missing-document issues.",
            ],
            "linked_document_ids": ["doc-tax-readme"],
            "linked_thread_ids": ["thread-w2"],
            "tags": ["W-2", "document retrieval", "email ops"],
            "default_prompt": "Summarize how the W-2 issue got resolved.",
            "draft_template": {
                "to": "josephjavery1@gmail.com",
                "subject": "Thanks for the W-2 follow-up",
                "body": "Hi Joe,\n\nThank you again for helping get the 2025 W-2 routed correctly. I have the accountant's attachment now and will use your personal Gmail address for any future follow-up.\n\nBest,\nChenyu",
            },
        },
    ],
    "risks": [
        {
            "id": "risk-tax-cascade",
            "severity": "critical",
            "title": "Tax residency position is still unresolved",
            "message": "The 1040 vs 1040-NR question changes the treatment of foreign gifts, foreign accounts, and the amendment plan.",
            "concern_id": "concern-1040nr",
        },
        {
            "id": "risk-3520",
            "severity": "critical",
            "title": "Form 3520 filing may be required for 2025",
            "message": "Repeated family wires and related-party aggregation create a non-trivial reporting risk with material penalties if missed.",
            "concern_id": "concern-3520",
        },
        {
            "id": "risk-sevis",
            "severity": "high",
            "title": "Open-ended SEVIS entries could create downstream questions",
            "message": "The employment record is evidence-heavy and should be cleaned using actual dates and supporting documents.",
            "concern_id": "concern-sevis",
        },
        {
            "id": "risk-passport",
            "severity": "high",
            "title": "Passport renewal can become a filing blocker",
            "message": "Counsel already said the full petition requires a valid passport and the renewal should not be delayed.",
            "concern_id": "concern-passport",
        },
    ],
    "deadlines": [
        _deadline(
            "dl-1040nr-2025",
            "2025 return strategy locked",
            date(2026, 4, 15),
            "tax",
            "concern-1040nr",
            "Finalize 1040-NR vs 1040 amendment plan before the main filing deadline.",
        ),
        _deadline(
            "dl-3520-2025",
            "Form 3520 readiness check",
            date(2026, 4, 15),
            "tax",
            "concern-3520",
            "Have a complete wire ledger, donor mapping, and reporting position ready.",
            auto_extend_to=date(2026, 10, 15),
        ),
        _deadline(
            "dl-passport",
            "Start passport renewal",
            date(2026, 3, 28),
            "immigration",
            "concern-passport",
            "Begin renewal now so the passport is valid for the H-1B full petition window.",
        ),
        _deadline(
            "dl-sevis",
            "Decide whether SEVIS cleanup is needed before petition prep",
            date(2026, 3, 31),
            "immigration",
            "concern-sevis",
            "Resolve whether open-ended employment entries should be corrected before filing.",
        ),
        _deadline(
            "dl-fanchen",
            "Fan Chen follow-up checkpoint",
            date(2026, 3, 21),
            "expert-routing",
            "concern-fanchen",
            "If there is no response, either send a second follow-up or move to the next tax contact.",
        ),
    ],
    "drafts": [],
}


class DemoWorkspaceStore:
    """In-memory seeded workspace for the web MVP."""

    def __init__(self):
        self._draft_sequence = count(1)
        self.state = deepcopy(INITIAL_STATE)

    def workspace(self) -> dict:
        data = deepcopy(self.state)
        data["stats"] = {
            "concerns_open": sum(
                1 for c in data["concerns"] if c["status"] not in {"resolved", "done"}
            ),
            "threads_unread": sum(1 for t in data["threads"] if t["unread"]),
            "deadlines_urgent": sum(
                1 for d in data["deadlines"] if d["status"] in {"urgent", "overdue"}
            ),
        }
        for session in data["discovery_sessions"]:
            captured = []
            follow_up = []
            for question in session["questions"]:
                if question["status"] == "captured":
                    captured.append(f"{question['label']}: {question['answer']}")
                else:
                    follow_up.append(question["follow_up_item"])
            session["captured_facts"] = captured
            session["missing_items"] = follow_up
            session["captured_count"] = len(captured)
            session["remaining_count"] = len(follow_up)
            total = len(session["questions"]) or 1
            session["progress_percent"] = round((len(captured) / total) * 100)
            session["upload_requests"] = [
                request for request in data["upload_requests"]
                if request["concern_id"] == session["concern_id"]
            ]
            session["ready_uploads"] = sum(
                1 for request in session["upload_requests"] if request["status"] == "ready"
            )
        return data

    def answer_discovery(self, question_id: str, answer: str) -> dict:
        for session in self.state["discovery_sessions"]:
            for question in session["questions"]:
                if question["id"] == question_id:
                    question["answer"] = answer
                    question["status"] = (
                        "needs_follow_up" if answer in UNRESOLVED_ANSWERS else "captured"
                    )
                    session["last_updated_at"] = datetime.now().isoformat(timespec="seconds")
                    return self.workspace()
        raise KeyError(question_id)

    def simulate_upload(self, request_id: str) -> dict:
        request = self._get_item("upload_requests", request_id)
        request["status"] = "ready"
        request["uploaded_at"] = datetime.now().isoformat(timespec="seconds")

        document_seed = deepcopy(request["document_seed"])
        document_seed["uploaded_at"] = request["uploaded_at"]
        document_seed["linked_concern_ids"] = [request["concern_id"]]

        if not any(doc["id"] == document_seed["id"] for doc in self.state["documents"]):
            self.state["documents"].insert(0, document_seed)

        job_id = f"job-{request_id}"
        try:
            job = self._get_item("ingestion_jobs", job_id)
            job["status"] = "ready"
            job["progress"] = 100
            job["detail"] = "Upload complete. Structured fields extracted and linked to the case record."
        except KeyError:
            self.state["ingestion_jobs"].insert(
                0,
                {
                    "id": job_id,
                    "concern_id": request["concern_id"],
                    "title": request["title"],
                    "status": "ready",
                    "progress": 100,
                    "detail": "Upload complete. Structured fields extracted and linked to the case record.",
                },
            )

        return self.workspace()

    def assistant_reply(self, prompt: str, concern_id: str | None = None) -> dict:
        prompt_normalized = (prompt or "").strip()
        focus = self._pick_concern(prompt_normalized, concern_id)
        documents = self._related_documents(focus["id"])
        threads = self._related_threads(focus["id"])
        deadlines = self._related_deadlines(focus["id"])
        risks = self._related_risks(focus["id"])

        sections = []
        prompt_lower = prompt_normalized.lower()

        if any(word in prompt_lower for word in {"draft", "follow-up", "reply", "email"}):
            sections.append(
                f"Focus concern: **{focus['title']}**. The highest-value next step is an outbound follow-up that keeps the evidence trail tight."
            )
        elif any(word in prompt_lower for word in {"missing", "need", "what am i missing"}):
            sections.append(
                f"Focus concern: **{focus['title']}**. The missing pieces are mostly evidence packaging and one confirmed expert answer."
            )
        elif any(word in prompt_lower for word in {"deadline", "due", "urgent"}):
            sections.append(
                f"Focus concern: **{focus['title']}**. The key issue is timing: the workspace already has a live deadline attached to this concern."
            )
        else:
            sections.append(
                f"Focus concern: **{focus['title']}**. Here is the current read from the workspace, not just from the chat history."
            )

        sections.append(focus["summary"])

        if risks:
            top_risk = risks[0]
            sections.append(
                f"Top risk: **{top_risk['title']}**. {top_risk['message']}"
            )

        if deadlines:
            soonest = sorted(deadlines, key=lambda item: item["due_date"])[0]
            sections.append(
                f"Nearest deadline: **{soonest['title']}** due **{soonest['due_date']}** with status **{soonest['status']}**."
            )

        if focus["next_steps"]:
            steps = "\n".join(f"- {item}" for item in focus["next_steps"][:3])
            sections.append(f"Recommended next actions:\n{steps}")

        citations = [
            {
                "kind": "document",
                "id": doc["id"],
                "label": doc["title"],
                "source_path": doc["source_path"],
            }
            for doc in documents[:3]
        ] + [
            {
                "kind": "thread",
                "id": thread["id"],
                "label": thread["subject"],
                "source_path": thread["counterpart"],
            }
            for thread in threads[:2]
        ]

        actions = []
        if focus.get("draft_template") and any(
            word in prompt_lower for word in {"draft", "follow-up", "reply", "email"}
        ):
            actions.append(
                {
                    "type": "draft_email",
                    "label": f"Create draft for {focus['title']}",
                    "concern_id": focus["id"],
                }
            )
        else:
            actions.append(
                {
                    "type": "draft_email",
                    "label": f"Draft follow-up for {focus['title']}",
                    "concern_id": focus["id"],
                }
            )

        return {
            "concern_id": focus["id"],
            "title": focus["title"],
            "text": "\n\n".join(sections),
            "citations": citations,
            "actions": actions,
        }

    def create_draft(self, concern_id: str) -> dict:
        concern = self._get_item("concerns", concern_id)
        template = concern.get("draft_template")
        if not template:
            raise KeyError(concern_id)

        draft_id = f"draft-{next(self._draft_sequence)}"
        draft = {
            "id": draft_id,
            "concern_id": concern_id,
            "title": concern["title"],
            "to": template["to"],
            "subject": template["subject"],
            "body": template["body"],
            "status": "draft",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.state["drafts"].insert(0, draft)
        return draft

    def send_draft(self, draft_id: str) -> dict:
        draft = self._get_item("drafts", draft_id)
        draft["status"] = "sent"
        draft["sent_at"] = datetime.now().isoformat(timespec="seconds")
        return draft

    def _pick_concern(self, prompt: str, concern_id: str | None) -> dict:
        if concern_id:
            return self._get_item("concerns", concern_id)

        prompt_lower = prompt.lower()
        for concern in self.state["concerns"]:
            search_blob = " ".join(
                [concern["title"], concern["summary"], " ".join(concern["tags"])]
            ).lower()
            if any(token in search_blob for token in prompt_lower.split()):
                return concern
        return self.state["concerns"][0]

    def _get_item(self, key: str, item_id: str) -> dict:
        for item in self.state[key]:
            if item["id"] == item_id:
                return item
        raise KeyError(item_id)

    def _related_documents(self, concern_id: str) -> list[dict]:
        return [
            doc for doc in self.state["documents"]
            if concern_id in doc["linked_concern_ids"]
        ]

    def _discovery_session(self, concern_id: str) -> dict:
        for session in self.state["discovery_sessions"]:
            if session["concern_id"] == concern_id:
                return session
        raise KeyError(concern_id)

    def _upload_requests_for(self, concern_id: str) -> list[dict]:
        return [
            request for request in self.state["upload_requests"]
            if request["concern_id"] == concern_id
        ]

    def _related_threads(self, concern_id: str) -> list[dict]:
        return [
            thread for thread in self.state["threads"]
            if concern_id in thread["linked_concern_ids"]
        ]

    def _related_deadlines(self, concern_id: str) -> list[dict]:
        return [
            deadline for deadline in self.state["deadlines"]
            if deadline["concern_id"] == concern_id
        ]

    def _related_risks(self, concern_id: str) -> list[dict]:
        ordered = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(
            [
                risk for risk in self.state["risks"]
                if risk["concern_id"] == concern_id
            ],
            key=lambda risk: ordered.get(risk["severity"], 99),
        )
