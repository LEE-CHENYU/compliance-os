"""Seeded MVP workspace data for the first runnable product-feel prototype."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from itertools import count

from compliance_os.compliance.schemas import Deadline


REFERENCE_DATE = date(2026, 3, 19)


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
    "documents": [
        {
            "id": "doc-tax-readme",
            "title": "2025 tax document tracker",
            "type": "tax",
            "source_path": "/Users/lichenyu/accounting/tax/2025/README.txt",
            "excerpt": "Residency determination needed: 1040 vs 1040-NR; NY and CA state filing implications; Claudius W-2 retrieval and employer correction context.",
            "linked_concern_ids": ["concern-1040nr", "concern-3520", "concern-w2"],
        },
        {
            "id": "doc-wolf-group",
            "title": "Wolf Group consultation request",
            "type": "expert-routing",
            "source_path": "/Users/lichenyu/accounting/outgoing/wolf_group/consultation_request_draft.txt",
            "excerpt": "Summarizes the full multi-year amendment issue: 1040 to 1040-NR, Form 5472/pro forma 1120, foreign gifts, foreign accounts, and state return questions.",
            "linked_concern_ids": ["concern-1040nr", "concern-fanchen"],
        },
        {
            "id": "doc-tax-register",
            "title": "Tax and compliance issues register",
            "type": "risk-register",
            "source_path": "/Users/lichenyu/accounting/concerns/tax_and_compliance_issues_021226.txt",
            "excerpt": "Tracks the cascade effect of filing as Form 1040, Form 3520 threshold analysis, possible FBAR/FATCA implications, and open lawyer questions.",
            "linked_concern_ids": ["concern-1040nr", "concern-3520"],
        },
        {
            "id": "doc-sevis-analysis",
            "title": "SEVIS employment record analysis",
            "type": "immigration",
            "source_path": "/Users/lichenyu/accounting/outgoing/columbia_isso/sevis_employment_analysis_030426.txt",
            "excerpt": "Maps OPT/STEM OPT/CPT periods, unemployment limits, open-ended SEVIS records, and a potential unauthorized-employment concern that needed documentary cleanup.",
            "linked_concern_ids": ["concern-sevis", "concern-passport"],
        },
        {
            "id": "doc-cindy-response",
            "title": "Cindy Chen CPT + passport response",
            "type": "legal-correspondence",
            "source_path": "/Users/lichenyu/accounting/outgoing/mt_law/cindy_cpt_passport_response_031426.txt",
            "excerpt": "Confirms passport renewal should happen sooner rather than later and that CPT at Yangtze depends on school rules for self-employment and unpaid positions.",
            "linked_concern_ids": ["concern-sevis", "concern-passport"],
        },
        {
            "id": "doc-wire-analysis",
            "title": "International wire and account analysis",
            "type": "financial",
            "source_path": "/Users/lichenyu/accounting/reports/Non_Zelle_Unmatched.txt",
            "excerpt": "Shows 7 international family wires, related-party gift concerns, business vs personal cash movements, and unresolved transfer destinations.",
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
        return data

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

