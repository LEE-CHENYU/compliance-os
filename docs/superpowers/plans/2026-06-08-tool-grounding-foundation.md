# Tool-Grounding Foundation Implementation Plan (Plan 1 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three highest-leverage tool-layer gaps from the cold-start onboarding spec so the extension can actually *deliver grounded artifacts* and *degrade gracefully* — a `save_artifact` tool, a correct zero-income Form 8843 route, and a clean empty-state for `guardian_status`.

**Architecture:** Three independent, surgical changes to the existing FastMCP server and one compliance check. No new subsystems. Each is a direct-call-testable Python function (the license gate is bypassed for direct calls, so tests need no licensing setup). TDD throughout: failing test → minimal implementation → green → commit.

**Tech Stack:** Python 3.11, FastMCP (`mcp[cli]>=1.10`), pytest 9.0.2, ruff 0.15.5. Package `compliance_os` (editable install). PDFs via PyMuPDF (`fitz`).

**Source spec:** `docs/superpowers/specs/2026-06-08-cold-start-onboarding-design.md` §8.1, §8.3, §8.5.

---

## Conventions (read once)

- **Interpreter / env:** the `compliance-os` conda env is the ONLY env with all deps. Either `conda activate compliance-os` first, or use the absolute interpreter below. Do NOT use `.venv` or conda `base` (they fail at conftest import).
- **Always run from the repo root** `/Users/lichenyu/compliance-os` (several tests load YAML by relative path).
- **Test command (single test):**
  ```bash
  /Users/lichenyu/miniconda3/envs/compliance-os/bin/python -m pytest <path>::<test> -v
  ```
  This document abbreviates that prefix as `PYTEST`. So `PYTEST tests/x.py::test_y -v` means the full command above.
- **Lint after each task:** `/Users/lichenyu/miniconda3/envs/compliance-os/bin/ruff check compliance_os/ && /Users/lichenyu/miniconda3/envs/compliance-os/bin/ruff format --check .`
- **Tests use inline strings, not real PDFs.** Service dirs that write to disk are redirected to `tmp_path` via `monkeypatch.setattr(module, "DIR_CONST", tmp_path / "...")` (established pattern in `tests/test_fbar_service.py`).

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `compliance_os/mcp_server.py` | MCP tool defs | Modify: add `save_artifact`; soften `guardian_status` offline return |
| `compliance_os/web/services/student_tax_check.py` | Student tax check | Modify: zero-income → standalone Form 8843 |
| `tests/test_save_artifact.py` | save_artifact tests | Create |
| `tests/test_student_tax_zero_income.py` | zero-income route tests | Create |
| `tests/test_mcp_server.py` | existing MCP tests | Modify: update `test_status_offline` expectation |

---

## Task 1: `save_artifact` MCP tool

Lets the model land a base64 artifact (e.g. the `pdf_base64` from `generate_form_8843`) at a real user-named path. Without this, every "saved to your folder" claim is unbacked (spec §8.1).

**Files:**
- Create: `tests/test_save_artifact.py`
- Modify: `compliance_os/mcp_server.py` (add a new tool after the `record_extracted_facts` function, ~line 781)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_save_artifact.py`:

```python
"""Tests for the save_artifact MCP tool."""

import base64
import json

from compliance_os.mcp_server import save_artifact


def test_save_artifact_writes_base64_and_creates_parent_dirs(tmp_path):
    payload = b"%PDF-1.4 fake pdf bytes"
    b64 = base64.b64encode(payload).decode("ascii")
    dest = tmp_path / "newdir" / "form-8843.pdf"  # parent does not exist yet

    result = json.loads(save_artifact(b64, str(dest)))

    assert result["status"] == "success"
    assert result["bytes_written"] == len(payload)
    assert dest.read_bytes() == payload
    assert result["path"] == str(dest.resolve())


def test_save_artifact_writes_text_when_is_text(tmp_path):
    dest = tmp_path / "83b-election-letter.txt"

    result = json.loads(save_artifact("Dear IRS, 83(b) election.", str(dest), is_text=True))

    assert result["status"] == "success"
    assert dest.read_text() == "Dear IRS, 83(b) election."


def test_save_artifact_rejects_invalid_base64_and_writes_nothing(tmp_path):
    dest = tmp_path / "x.pdf"

    result = json.loads(save_artifact("not!!valid!!base64", str(dest)))

    assert result["status"] == "error"
    assert not dest.exists()


def test_save_artifact_rejects_empty_path():
    result = json.loads(save_artifact("aGk=", "   "))
    assert result["status"] == "error"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTEST tests/test_save_artifact.py -v`
Expected: FAIL at import — `ImportError: cannot import name 'save_artifact' from 'compliance_os.mcp_server'`

- [ ] **Step 3: Implement the tool**

In `compliance_os/mcp_server.py`, immediately after the `record_extracted_facts` function (it ends ~line 781, returning `json.dumps(local_record_extracted_facts(...))`), add:

```python
@mcp.tool(
    annotations=ToolAnnotations(
        title="Save artifact to disk",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def save_artifact(content_base64: str, output_path: str, is_text: bool = False) -> str:
    """Write a generated artifact (PDF, form, letter) to a path on disk.

    Use this to land an artifact returned by another tool — e.g. the
    `pdf_base64` from generate_form_8843 — at a real, user-visible
    location. Runs locally; nothing leaves the machine. Parent
    directories are created if missing. Tell the user the returned
    `path` so they can find the file.

    Args:
        content_base64: The artifact bytes, base64-encoded. When
            is_text=True this is instead treated as raw UTF-8 text.
        output_path: Absolute or ~-relative path to write to.
        is_text: When True, write content_base64 as plain UTF-8 text
            rather than base64-decoding it.
    """
    if not output_path or not output_path.strip():
        return json.dumps({"status": "error", "error": "output_path is empty"})
    try:
        if is_text:
            data = content_base64.encode("utf-8")
        else:
            data = base64.b64decode(content_base64, validate=True)
    except Exception as exc:
        return json.dumps({"status": "error", "error": f"Invalid base64: {exc}"})
    try:
        dest = Path(output_path).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return json.dumps({
            "status": "success",
            "path": str(dest.resolve()),
            "bytes_written": len(data),
        })
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)})
```

(`base64`, `json`, and `Path` are already imported at the top of the file; `ToolAnnotations` is imported from `mcp.types`. Gating is automatic by tool name and `GatedMCP.add_tool` forces `structured_output=False`, so no extra wiring is needed.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTEST tests/test_save_artifact.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Lint**

Run: `/Users/lichenyu/miniconda3/envs/compliance-os/bin/ruff check compliance_os/mcp_server.py tests/test_save_artifact.py`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add compliance_os/mcp_server.py tests/test_save_artifact.py
git commit -m "feat(mcp): add save_artifact tool to land base64 artifacts on disk"
```

---

## Task 2: Route zero-income filers to a standalone June-15 Form 8843

`process_student_tax_check` hardwires `has_us_income=True`/`filing_with_tax_return=True`, which forces the **April-15** package deadline and always emits a 1040-NR package — even for a user with no income, who actually files a **standalone Form 8843 due June 15** (spec §8.3; the wrong-deadline bug the simulation flagged for the Raj/8843 persona).

**Files:**
- Create: `tests/test_student_tax_zero_income.py`
- Modify: `compliance_os/web/services/student_tax_check.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_student_tax_zero_income.py`:

```python
"""Zero-income students should be routed to a standalone Form 8843, not a 1040-NR package."""

import compliance_os.web.services.student_tax_check as mod


def _run(monkeypatch, tmp_path, **inputs):
    monkeypatch.setattr(mod, "STUDENT_TAX_DIR", tmp_path / "student_tax")
    base = {
        "tax_year": 2025,
        "full_name": "Test Student",
        "visa_type": "F-1",
        "school_name": "State University",
        "country_citizenship": "India",
    }
    base.update(inputs)
    return mod.process_student_tax_check("test-order", base)


def test_zero_income_routes_to_standalone_june_15(monkeypatch, tmp_path):
    result = _run(monkeypatch, tmp_path, wage_income_usd=0, scholarship_income_usd=0, other_income_usd=0)

    assert result["requires_1040nr"] is False
    assert result["filing_deadline"] == "2026-06-15"
    filenames = [a["filename"] for a in result["artifacts"]]
    assert "form-8843.pdf" in filenames
    assert "1040nr-package-summary.pdf" not in filenames


def test_income_keeps_1040nr_package_and_april_15(monkeypatch, tmp_path):
    result = _run(monkeypatch, tmp_path, wage_income_usd=25000)

    assert result["requires_1040nr"] is True
    assert result["filing_deadline"] == "2026-04-15"
    filenames = [a["filename"] for a in result["artifacts"]]
    assert "1040nr-package-summary.pdf" in filenames
    assert "form-8843.pdf" in filenames
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTEST tests/test_student_tax_zero_income.py -v`
Expected: FAIL — `test_zero_income_routes_to_standalone_june_15` fails on `KeyError: 'requires_1040nr'` (the key does not exist yet); after that is added it would still fail on `filing_deadline == "2026-04-15"` and the package being present.

- [ ] **Step 3: Add the `requires_1040nr` determinant**

In `compliance_os/web/services/student_tax_check.py`, change line 59 (the `total_income` assignment) to also derive the flag:

```python
    total_income = wage_income + scholarship_income + other_income
    requires_1040nr = total_income > 0
```

- [ ] **Step 4: Make the Form 8843 filing posture conditional**

Change lines 429-430 (inside the `form_8843_inputs` dict) from:

```python
        "filing_with_tax_return": True,
        "has_us_income": True,
    }
```

to:

```python
        "filing_with_tax_return": requires_1040nr,
        "has_us_income": requires_1040nr,
    }
```

- [ ] **Step 5: Make the deadline follow the filing posture**

Immediately after line 432 (`filing_context = build_form_8843_filing_context(form_8843_inputs)`), add:

```python
    # A true zero-income filer mails a standalone Form 8843 (due June 15),
    # not a 1040-NR package (due April 15). build_form_8843_filing_context
    # already computes the correct deadline from has_us_income, so adopt it
    # as the single source of truth.
    _ctx_deadline = filing_context.get("filing_deadline")
    if isinstance(_ctx_deadline, date):
        deadline = _ctx_deadline
```

(`date` is already imported at line 5.)

- [ ] **Step 6: Skip the 1040-NR package PDF for zero-income**

Replace lines 477-514 (the `package_path = ...` write through the end of the `else:` artifacts block) with:

```python
    if not requires_1040nr:
        # Zero income → standalone Form 8843 only. Don't generate a 1040-NR
        # package the user doesn't need.
        artifacts = [
            {
                "label": "Download Form 8843 (mail standalone — no 1040-NR needed)",
                "filename": form_8843_path.name,
                "path": str(form_8843_path),
            },
        ]
    else:
        package_path = artifacts_dir / "1040nr-package-summary.pdf"
        package_path.write_bytes(
            build_text_pdf(
                "Student Tax Package Summary",
                package_lines,
                subtitle=f"Tax year {tax_year}",
            )
        )
        if spt_crossover_warning:
            # When SPT crossover fires, the user is likely a RESIDENT alien and
            # neither 1040-NR nor Form 8843 applies. Relabel artifacts as
            # advisor-review-only to prevent the user from filing the wrong form.
            artifacts = [
                {
                    "label": "Download 1040-NR package summary (REVIEW ONLY — wrong form if you are a resident alien)",
                    "filename": package_path.name,
                    "path": str(package_path),
                },
                {
                    "label": "Download Form 8843 (REVIEW ONLY — does not apply to resident aliens)",
                    "filename": form_8843_path.name,
                    "path": str(form_8843_path),
                },
            ]
        else:
            artifacts = [
                {
                    "label": "Download 1040-NR package summary",
                    "filename": package_path.name,
                    "path": str(package_path),
                },
                {
                    "label": "Download Form 8843",
                    "filename": form_8843_path.name,
                    "path": str(form_8843_path),
                },
            ]
```

- [ ] **Step 7: Make the next-steps coherent for zero-income**

Replace lines 586-590 (the `next_steps.extend([...])` block that ends with `f"File the return package by {deadline.isoformat()} and attach Form 8843.",` and `])`) with:

```python
    if requires_1040nr:
        next_steps.extend([
            f"Review the 1040-NR package summary against your {docs_phrase}.",
            "Prepare the 1040-NR using nonresident-aware software (Sprintax or GLACIER Tax Prep) or a CPA familiar with nonresident filings — standard consumer software (TurboTax, H&R Block, FreeTaxUSA) cannot produce a valid 1040-NR.",
            f"File the return package by {deadline.isoformat()} and attach Form 8843.",
        ])
    else:
        next_steps.extend([
            "You reported no U.S. income, so you likely only need to mail a standalone Form 8843 — not a 1040-NR return.",
            "Print the Form 8843, sign and date it, and mail it to the IRS in Austin, TX (see the filing guidance below).",
            f"Mail it by the standalone deadline, {deadline.isoformat()}. Use USPS Certified Mail for proof of filing.",
        ])
```

- [ ] **Step 8: Expose the determinant in the return dict**

Change the end of the return dict (line 615) from:

```python
        "total_income_usd": total_income,
    }
```

to:

```python
        "total_income_usd": total_income,
        "requires_1040nr": requires_1040nr,
    }
```

- [ ] **Step 9: Run the tests to verify they pass**

Run: `PYTEST tests/test_student_tax_zero_income.py -v`
Expected: PASS (2 passed)

- [ ] **Step 10: Run the existing student-tax test to confirm no regression**

Run: `PYTEST tests/test_student_tax_check_service.py -v` (if present; otherwise `PYTEST tests/ -k student_tax -v`)
Expected: PASS (existing income-path tests still green — the with-income branch is unchanged)

- [ ] **Step 11: Lint**

Run: `/Users/lichenyu/miniconda3/envs/compliance-os/bin/ruff check compliance_os/web/services/student_tax_check.py tests/test_student_tax_zero_income.py`
Expected: `All checks passed!`

- [ ] **Step 12: Commit**

```bash
git add compliance_os/web/services/student_tax_check.py tests/test_student_tax_zero_income.py
git commit -m "fix(student_tax): route zero-income filers to standalone June-15 Form 8843"
```

---

## Task 3: Graceful empty-state for `guardian_status` when the local API is down

At cold start the local API may not be running; `guardian_status` currently returns a raw `Error: <exc>` string. The design's principle #10 wants READ-STATE tools to degrade gracefully (spec §8.5).

**Files:**
- Modify: `compliance_os/mcp_server.py` (the `guardian_status` except clause, ~lines 433-434)
- Modify: `tests/test_mcp_server.py` (update the existing `test_status_offline` expectation)

- [ ] **Step 1: Update the existing test to the new expectation (the failing test)**

In `tests/test_mcp_server.py`, find `def test_status_offline` (decorated with `@patch("compliance_os.mcp_server._api_get", new_callable=AsyncMock, side_effect=RuntimeError("Connection refused"))`). Replace its body assertion:

```python
        result = _run(guardian_status())
        assert "Error" in result
```

with:

```python
        result = _run(guardian_status())
        assert "Error:" not in result
        assert "Guardian Compliance Status" in result
        assert "isn't reachable" in result
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTEST "tests/test_mcp_server.py" -k test_status_offline -v`
Expected: FAIL — current code returns `"Error: Cannot reach Guardian API ..."`, so `assert "Error:" not in result` fails.

- [ ] **Step 3: Soften the offline return**

In `compliance_os/mcp_server.py`, in `guardian_status`, change the except clause (lines 433-434) from:

```python
    except RuntimeError as exc:
        return f"Error: {exc}"
```

to:

```python
    except RuntimeError:
        return (
            "# Guardian Compliance Status\n\n"
            "_Guardian's local store isn't reachable yet — nothing has been set up "
            "on this machine, or the local app isn't running — so there's no status "
            "to show._\n\n"
            "That's normal on a fresh start. Tell me what you're trying to figure out "
            "(for example: an F-1 internship, a Form 5472 question, an 83(b) clock), or "
            "point me at a document, and I'll work from that directly."
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTEST "tests/test_mcp_server.py" -k test_status_offline -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Lint**

Run: `/Users/lichenyu/miniconda3/envs/compliance-os/bin/ruff check compliance_os/mcp_server.py`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add compliance_os/mcp_server.py tests/test_mcp_server.py
git commit -m "fix(mcp): graceful empty-state for guardian_status when local API is down"
```

---

## Final verification

- [ ] **Run the full touched-area test set**

Run:
```bash
/Users/lichenyu/miniconda3/envs/compliance-os/bin/python -m pytest \
  tests/test_save_artifact.py \
  tests/test_student_tax_zero_income.py \
  tests/test_mcp_server.py -v
```
Expected: all green.

- [ ] **Sanity-check the broader suite didn't regress**

Run: `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python -m pytest tests/ -q`
Expected: no NEW failures vs. baseline (record any pre-existing failures before starting).

---

## Self-Review (completed during authoring)

**Spec §8 coverage by this plan:**
- §8.1 `save_artifact` → Task 1 ✓
- §8.3 `student_tax` zero-income hardwiring → Task 2 ✓
- §8.5 clean empty-state for READ-STATE tools → Task 3 ✓ (`guardian_status`; `guardian_deadlines`/`guardian_risks` share the identical 2-line pattern at ~512-513 / ~546-547 — fold them in as a trivial follow-up if desired)
- §8.5 Gmail draft-by-default → **already satisfied** in the codebase: `_gmail_guard` returns `gmail_not_configured` and defers to the user's own connector unless `~/.config/guardian/gmail_credentials.json` exists. No code change; surface this as guidance in Plan 4.
- §8.2 template PII leakage → **Plan 3** (below)
- §8.4 classifier labels → **Plan 2** (below)
- §8.5 `set_user_fact` track taxonomy + mandatory attorney hedge → **Plan 4** (instruction-level)

**Placeholder scan:** none — every code step shows complete code; every test step shows complete tests; every run step gives an exact command + expected output.

**Type/name consistency:** `requires_1040nr` (bool) is defined in Task 2 Step 3 and used consistently in Steps 4/6/7/8. `save_artifact(content_base64, output_path, is_text)` signature matches its tests. `STUDENT_TAX_DIR` is the real module constant being monkeypatched.

---

## Roadmap — remaining plans (write these next, one at a time)

**Plan 2 — Document classifier + extraction labels (spec §8.4).** Add fully-wired doc types `i797` (complete the half-wired one), `i130`, `i485`, `lca`, `ds2019`, `advance_parole`/`i512`. Per type, edits land in: `compliance_os/web/services/classifier.py` (`FILENAME_PATTERNS`, `PATTERNS`, `TEXT_MIN_MATCHES`, `DOC_TYPE_ALIASES`), `compliance_os/facts/vocabulary.py` (new `FactDef`s — note: advance-parole needs its OWN expiry key, NOT `ead`'s STEM-OPT-wired `valid_to`; LCA needs SOC/wage-level/title), and `compliance_os/facts/extraction_map.py` (`EXTRACTION_TO_FACT_KEY` rows, which double as the extraction schema). Tests mirror `tests/test_classifier_service.py` (inline-text `classify_text(...).doc_type`) and `tests/test_extraction_rehome.py` (`schema_for_doc_type` + projection). One task per doc type keeps it bite-sized.

**Plan 3 — Generic, PII-free case templates (spec §8.2).** The `h1b.py` (48 slots) and `cpa.py` (28 slots) templates are one real user's case (Columbia/CIAM, BSGC/BitSync) and leak via `case_active_search`. Build sanitized generic templates + add `founder_h1b`, `5472`, `eb1a_evidence`, `dependent_status`, register them in `case_templates/validator.py`, and gate `case_active_search` against arbitrary-user leakage. Larger refactor — its own plan.

**Plan 4 — Onboarding/router server instructions (spec §3–§7).** Bake the universal 3-turn opening, the routing decision tree (scope/ownership/dependent forks), and the cold-start principles into the `GatedMCP(instructions=...)` block (and/or a routing reference doc the model reads), plus the `set_user_fact` track taxonomy and the mandatory attorney-hedge rule. "Tests" here are eval-style (assert the instruction text covers each workflow's trigger signals), not unit tests.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-08-tool-grounding-foundation.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
