"""
Precision-first heuristic backstop for the "claimed a tool result with no call" fabrication mode.

This linter detects assistant prose that asserts a tool ran or returned a result when no matching
tool call was actually made in that turn. It is NOT a substitute for the model following
GUARDIAN_INSTRUCTIONS — it is a deterministic detector that a host or QA layer can run over
a completed turn to catch the specific fabrication pattern observed in e2e testing (e.g. the model
narrating "I ran the 83(b) check, it confirms…" with no actual call).

Design principle: HIGH PRECISION over recall.  A false positive on honest phrasing (offers,
future tense, labeled reasoning) erodes trust in the linter more than a missed positive.
Guards are applied before flagging; a match only fires when no backing tool call and no
future/conditional/labeled-reasoning context is present.
"""

from __future__ import annotations

import dataclasses
import re


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Flag:
    claim_type: str
    matched_phrase: str
    required_any: tuple[str, ...]
    reason: str


# ---------------------------------------------------------------------------
# Future / offer / conditional left-context cues
# If any of these appear within LEFT_WINDOW characters BEFORE a match start,
# the rule is suppressed (the statement is an offer or conditional, not a claim).
# ---------------------------------------------------------------------------

_FUTURE_CUES: list[str] = [
    "i'll",
    "i will",
    "i can",
    "i'd",
    "i would",
    "once you",
    "as soon as",
    "when you",
    "if you",
    "if your",
    "if the",
    "ready to",
    "happy to",
    "let me know",
    "send me",
    "give me",
    "i'm ready to",
    "i won't guess",
    "i won't",
    "point me",
]

LEFT_WINDOW = 60  # characters to scan left of a match for future cues

_SENT_BOUNDARY_RE = re.compile(r"[.\n;!?]")


def _has_future_cue(text_lower: str, match_start: int) -> bool:
    """Return True if a future/conditional/offer cue appears in the left context.

    The window is clipped at the nearest sentence boundary so that a cue in a
    PRIOR sentence (e.g. a sign-off like "Let me know.") does not suppress a
    genuine claim in the current sentence.
    """
    window_start = max(0, match_start - LEFT_WINDOW)
    left_ctx = text_lower[window_start:match_start]
    boundaries = [m.end() for m in _SENT_BOUNDARY_RE.finditer(left_ctx)]
    if boundaries:
        left_ctx = left_ctx[boundaries[-1]:]
    return any(cue in left_ctx for cue in _FUTURE_CUES)


# ---------------------------------------------------------------------------
# Labeled-reasoning cues (ran_check only)
# If any of these appear in the SAME SENTENCE as the match, the rule is suppressed.
# ---------------------------------------------------------------------------

_REASONING_LABELS: list[str] = [
    r"my read",
    r"not a computed check",
    r"not a real check",
    r"not a check",
    r"not a number my tools compute",
    r"the 30-day rule",
    r"the rule",
]

_REASONING_RE = re.compile(
    "|".join(_REASONING_LABELS),
    re.IGNORECASE,
)


def _extract_sentence(text: str, match_start: int, match_end: int) -> str:
    """Return the sentence-ish fragment containing the match."""
    # Walk backward to sentence boundary
    start = max(0, text.rfind(".", 0, match_start))
    # Walk forward to sentence boundary
    end = text.find(".", match_end)
    if end == -1:
        end = len(text)
    return text[start:end]


def _has_reasoning_label(text: str, match_start: int, match_end: int) -> bool:
    sentence = _extract_sentence(text, match_start, match_end)
    return bool(_REASONING_RE.search(sentence))


# Read-document non-claim cues: when the assistant is INSTRUCTING the user to read
# a field, disclaiming that it read the doc, or speaking conditionally, it is not
# asserting an extracted value — suppress the read_document rule for that sentence.
_READ_NONCLAIM_RE = re.compile(
    "|".join([
        r"i haven'?t opened", r"haven'?t read", r"i can'?t see", r"without reading",
        r"you enter", r"transcrib", r"tell me", r"read it to me", r"you'?ll need",
        r"check the top", r"let me know", r"if your", r"if the", r"point me", r"send me",
    ]),
    re.IGNORECASE,
)


def _is_read_nonclaim(text: str, match_start: int, match_end: int) -> bool:
    return bool(_READ_NONCLAIM_RE.search(_extract_sentence(text, match_start, match_end)))


# ---------------------------------------------------------------------------
# Rule definitions
# Each rule: (claim_type, [compiled regexes], required_any_tools, reason_text)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class _Rule:
    claim_type: str
    patterns: list[re.Pattern[str]]
    required_any: tuple[str, ...]
    reason: str


def _cp(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


_RULES: list[_Rule] = [
    _Rule(
        claim_type="ran_check",
        patterns=[
            # "I just ran the real 83(b) check", "I ran the check", "ran a check"
            _cp(r"\b(i\s+)?(just\s+)?ran\s+(the\s+|a\s+|run_compliance_check\s*|the\s+real\s+)?"
                r"[\w().\-]*?\s*\bcheck\b"),
            # "the check confirms / returns / shows / says"
            _cp(r"\bthe\s+check\s+(confirms|returns|shows|says)\b"),
            # "from the check" / "per the check" — implies a result was retrieved
            _cp(r"\bfrom\s+the\s+check\b"),
            _cp(r"\bper\s+the\s+check\b"),
            # "the check came back (clean)" — a completed check result
            _cp(r"\bcheck\s+came\s+back\b"),
            # "It confirms the 30-day window" when following a check statement
            _cp(r"\bit\s+(confirms|returns)\s+(the\s+)?\d"),
            # Bare "it confirms" (sentence-level — will be guarded by context)
            _cp(r"\bIt\s+confirms\b"),
            # "confirms the 30-day window" as a standalone phrase
            _cp(r"\bconfirms\s+the\s+30.day\s+window\b"),
        ],
        required_any=("run_compliance_check", "get_filing_guidance"),
        reason=(
            "Message claims a compliance check ran and returned a result, "
            "but no check tool was called this turn."
        ),
    ),
    _Rule(
        claim_type="read_document",
        patterns=[
            # "Your I-20 shows X", "your EAD says", "your document lists/has"
            _cp(r"\byour\s+(i-?20|ead|document|passport|i-?983|lca|file|card)\s+(shows|says|lists|has)\b"),
            # "I read/pulled/lifted <field> (straight) off your/the document/I-20/card"
            _cp(r"\b(read|parsed|pulled|lifted|got)\b[\w\s'-]{0,40}?\b(straight\s+)?off\s+"
                r"(your|the)\s+(document|i-?20|ead|card|file)\b"),
            # "read/parsed/pulled it off/from your document/I-20/file"
            _cp(r"\b(read|parsed|pulled|lifted|got)\s+(it\s+|them\s+)?(off|from)\s+"
                r"your\s+(document|i-?20|file|card)\b"),
            # "From your I-20, <value>" — value asserted off the document. Guarded
            # below by the non-claim filter so instructing/disclaiming uses don't fire.
            _cp(r"\bfrom\s+your\s+(i-?20|document|file|ead|card)\b"),
        ],
        required_any=("parse_document",),
        reason=(
            "Message asserts specific field values extracted from a user document, "
            "but no document-parsing tool was called this turn."
        ),
    ),
    _Rule(
        claim_type="saved_file",
        patterns=[
            # "I've saved the form / file / PDF / it / this to ..."
            _cp(r"\b(i'?ve\s+|i\s+)?saved\s+(it|the\s+file|the\s+pdf|the\s+form|the\s+document|this|your|the\s+completed)\b"),
            # "saved it to your/~//"
            _cp(r"\bsaved\s+(it\s+)?to\s+(your|~|/)"),
            # "saved to your folder"
            _cp(r"\bsaved\s+to\s+your\s+\w+\s+folder\b"),
        ],
        required_any=("save_artifact",),
        reason=(
            "Message claims a file was saved, "
            "but no save_artifact tool was called this turn."
        ),
    ),
    _Rule(
        claim_type="search_results",
        patterns=[
            # "shortlist is finishing/running/complete/done"
            _cp(r"\b(the\s+)?(shortlist|search)\s+is\s+(running|finishing|complete|done)\b"),
            # "here are the named firms / attorneys"
            _cp(r"\bhere\s+are\s+the\s+(named\s+)?(firms|attorneys)\b"),
            # "I found these firms / I have the attorneys"
            _cp(r"\bi\s+(found|have)\s+(these\s+|the\s+)?(firms|attorneys)\b"),
            # "your (vetted) shortlist" / verbless "shortlist: <names>"
            _cp(r"\byour\s+(vetted\s+)?shortlist\b"),
            _cp(r"\b(vetted\s+)?shortlist\s*[:\-]"),
        ],
        required_any=("lawyer_search_ingest",),
        reason=(
            "Message presents search results (firms/attorneys), "
            "but no ingest tool was called this turn — only a plan tool was."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Core detection
# ---------------------------------------------------------------------------

def flag_unbacked_tool_claims(message: str, tools_called: list[str]) -> list[Flag]:
    """
    Scan *message* for unbacked tool-result claims and return a list of :class:`Flag` objects.

    A claim is "unbacked" when:
    - It matches a completed-result pattern for a claim_type, AND
    - None of the ``required_any`` tools appear in ``tools_called``, AND
    - No future/offer/conditional cue appears in the left context of the match, AND
    - (for ran_check) no labeled-reasoning phrase appears in the same sentence.

    One flag per claim_type at most (de-duplicated).
    """
    tools_set = set(tools_called)
    text_lower = message.lower()
    seen_types: set[str] = set()
    flags: list[Flag] = []

    for rule in _RULES:
        if rule.claim_type in seen_types:
            continue

        # Skip if the claim is backed by a required tool
        if any(t in tools_set for t in rule.required_any):
            continue

        for pattern in rule.patterns:
            if rule.claim_type in seen_types:
                break

            for m in pattern.finditer(message):
                # Guard 1: future/offer/conditional left-context
                if _has_future_cue(text_lower, m.start()):
                    continue

                # Guard 2: labeled-reasoning (ran_check only)
                if rule.claim_type == "ran_check" and _has_reasoning_label(
                    message, m.start(), m.end()
                ):
                    continue

                # Guard 3: read_document non-claim (instructing / disclaiming / conditional)
                if rule.claim_type == "read_document" and _is_read_nonclaim(
                    message, m.start(), m.end()
                ):
                    continue

                # All guards passed — emit flag
                flags.append(
                    Flag(
                        claim_type=rule.claim_type,
                        matched_phrase=m.group(0),
                        required_any=rule.required_any,
                        reason=rule.reason,
                    )
                )
                seen_types.add(rule.claim_type)
                break  # one flag per claim_type

    return flags


def lint_turn(message: str, tools_called: list[str]) -> dict:
    """
    Run :func:`flag_unbacked_tool_claims` and return a summary dict.

    Returns::

        {
            "ok": bool,        # True when no flags
            "flags": [         # list of flag dicts (empty when ok)
                {
                    "claim_type": str,
                    "matched_phrase": str,
                    "required_any": tuple[str, ...],
                    "reason": str,
                }
            ]
        }
    """
    flags = flag_unbacked_tool_claims(message, tools_called)
    return {
        "ok": len(flags) == 0,
        "flags": [dataclasses.asdict(f) for f in flags],
    }
