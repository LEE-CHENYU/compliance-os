"""Scorecard + markdown renderer for check-quality verdicts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .judge import JudgeVerdict


@dataclass
class Scorecard:
    verdicts: list[JudgeVerdict]
    total_tokens_in: int = 0
    total_tokens_out: int = 0

    @property
    def total_cases(self) -> int:
        return len(self.verdicts)

    @property
    def pass_count(self) -> int:
        return sum(1 for v in self.verdicts if v.overall == "pass")

    @property
    def partial_count(self) -> int:
        return sum(1 for v in self.verdicts if v.overall == "partial")

    @property
    def fail_count(self) -> int:
        return sum(1 for v in self.verdicts if v.overall == "fail")

    def by_service(self) -> dict[str, list[JudgeVerdict]]:
        grouped: dict[str, list[JudgeVerdict]] = {}
        for v in self.verdicts:
            grouped.setdefault(v.service, []).append(v)
        return grouped


def _rating_emoji(rating: str) -> str:
    return {"pass": "✅", "partial": "⚠️ ", "fail": "❌"}.get(rating, "❓")


def render_markdown(scorecard: Scorecard) -> str:
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append("# Check Quality Scorecard")
    lines.append("")
    lines.append(f"Generated {now} — judge: claude-opus-4-6 (adaptive thinking)")
    lines.append("")
    lines.append(
        f"**Totals:** {scorecard.pass_count} pass · {scorecard.partial_count} partial · "
        f"{scorecard.fail_count} fail · {scorecard.total_cases} cases"
    )
    lines.append(
        f"**Tokens:** {scorecard.total_tokens_in:,} in · {scorecard.total_tokens_out:,} out"
    )
    lines.append("")

    for service, verdicts in scorecard.by_service().items():
        lines.append(f"## {service}")
        lines.append("")
        passes = sum(1 for v in verdicts if v.overall == "pass")
        partials = sum(1 for v in verdicts if v.overall == "partial")
        fails = sum(1 for v in verdicts if v.overall == "fail")
        lines.append(f"_{passes} pass · {partials} partial · {fails} fail_")
        lines.append("")

        for v in verdicts:
            lines.append(f"### {_rating_emoji(v.overall)} `{v.scenario_label}` — {v.overall.upper()}")
            lines.append("")
            if v.cached:
                lines.append("_(cached verdict)_")
                lines.append("")
            lines.append("| Dimension | Rating | Reasoning |")
            lines.append("|---|---|---|")
            for d in v.dimensions:
                reasoning = d.reasoning.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {d.name} | {_rating_emoji(d.rating)} {d.rating} | {reasoning} |")
            lines.append("")
            if v.notes:
                lines.append(f"**Notes:** {v.notes}")
                lines.append("")

    return "\n".join(lines)
