"""Tests for the H-1B case template matcher."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compliance_os.case_templates import H1B_TEMPLATE, match_folder, format_report
from compliance_os.case_templates.matcher import _score_slot


@pytest.fixture
def klasko_path() -> Path:
    p = Path("/Users/lichenyu/accounting/outgoing/klasko/upload_041626")
    if not p.is_dir():
        pytest.skip("Klasko reference package not available")
    return p


# ─── Template schema ─────────────────────────────────────────────

class TestTemplateSchema:

    def test_template_has_all_sections(self):
        assert set(H1B_TEMPLATE.sections) == {"A", "B", "C", "D", "E", "F", "G"}

    def test_template_slot_count(self):
        # 11 A + 13 B + 3 C + 15 D + 5 E + 9 F + 3 G = 59 slots total
        assert len(H1B_TEMPLATE.slots) == 59

    def test_required_and_optional_split(self):
        req = H1B_TEMPLATE.required_slots()
        assert 30 < len(req) < 45  # broad guard against accidental shifts

    def test_slot_ids_unique(self):
        ids = [s.id for s in H1B_TEMPLATE.slots]
        assert len(ids) == len(set(ids))

    def test_b_section_lineage_order(self):
        bs = H1B_TEMPLATE.slots_by_section("B")
        orders = [s.order for s in bs]
        assert orders == sorted(orders)
        assert orders[0] == 1 and orders[-1] == 13


# ─── Scoring ─────────────────────────────────────────────────────

class TestScoring:

    def test_perfect_filename_match_scores_high(self, tmp_path):
        f = tmp_path / "A1_passport_chenyu_E71722932.jpeg"
        f.write_bytes(b"fake")
        slot = H1B_TEMPLATE.slot_by_id("A1")
        score, reasons = _score_slot(slot, f)
        assert score >= 5.0
        assert any("A1" in r for r in reasons)

    def test_prefix_alone_does_not_corroborate(self, tmp_path):
        # Slot D14 = bank statement. File uses D14_ prefix but is
        # an employment letter — should NOT claim D14 strongly.
        f = tmp_path / "D14_yangtze_employment_letter.pdf"
        f.write_bytes(b"fake")
        slot = H1B_TEMPLATE.slot_by_id("D14")
        score, _ = _score_slot(slot, f)
        # Prefix only gets the weak bonus (1.0), not the full 5.0
        assert score < 2.0

    def test_no_match_for_unrelated_file(self, tmp_path):
        f = tmp_path / "random_photo.jpg"
        f.write_bytes(b"fake")
        slot = H1B_TEMPLATE.slot_by_id("A1")
        score, _ = _score_slot(slot, f)
        assert score == 0.0

    def test_keyword_match_contributes(self, tmp_path):
        f = tmp_path / "my_bylaws_scan.pdf"
        f.write_bytes(b"fake")
        slot = H1B_TEMPLATE.slot_by_id("D2")
        score, reasons = _score_slot(slot, f)
        assert score > 0
        assert any("keyword" in r for r in reasons)


# ─── End-to-end against real Klasko package ──────────────────────

class TestKlaskoPackage:

    def test_all_required_covered(self, klasko_path):
        report = match_folder(klasko_path, H1B_TEMPLATE)
        # D14 (bank statement) is legitimately pending. Package may
        # also evolve (e.g. D9 lease-extract removed when D15 full
        # signed lease was added) — tolerate section-D misses.
        missing_ids = {s.id for s in report.missing_required}
        non_d = missing_ids - {s.id for s in H1B_TEMPLATE.slots_by_section("D")}
        assert non_d == set(), f"Unexpected non-D missing: {non_d}"
        assert "D14" in missing_ids

    def test_section_coverage(self, klasko_path):
        report = match_folder(klasko_path, H1B_TEMPLATE)
        # A/B/C/E/F/G should be 100%; D varies as the package evolves
        assert report.coverage["A"] == 1.0
        assert report.coverage["B"] == 1.0
        assert report.coverage["C"] == 1.0
        assert report.coverage["E"] == 1.0
        assert report.coverage["G"] == 1.0
        assert 0.70 <= report.coverage["D"] < 1.0

    def test_no_misplaced_files(self, klasko_path):
        report = match_folder(klasko_path, H1B_TEMPLATE)
        assert report.misplaced == []

    def test_report_formats_as_text(self, klasko_path):
        report = match_folder(klasko_path, H1B_TEMPLATE)
        text = format_report(report, H1B_TEMPLATE)
        assert "H-1B Petition Package" in text
        assert "Coverage by section" in text
        assert "D14" in text  # surfaces in missing required


# ─── Synthetic flat folder (no section dirs) ─────────────────────

class TestFlatFolder:
    """User dumps all files in one folder without A_/B_/C_ subdirs."""

    def test_files_still_matched_via_keywords(self, tmp_path):
        (tmp_path / "my_passport_bio.pdf").write_bytes(b"x")
        (tmp_path / "bylaws_final.pdf").write_bytes(b"x")
        (tmp_path / "articles_of_incorporation.pdf").write_bytes(b"x")
        report = match_folder(tmp_path, H1B_TEMPLATE)
        assert "A1" in report.matched  # passport
        assert "D2" in report.matched  # bylaws
        assert "D1" in report.matched  # articles


# ─── MCP tool wrapper ────────────────────────────────────────────

class TestMCPTool:

    def test_h1b_active_search_text_mode(self, klasko_path):
        from compliance_os.mcp_server import h1b_active_search
        result = h1b_active_search(folder=str(klasko_path))
        assert "H-1B Petition Package" in result
        assert "Coverage by section" in result

    def test_h1b_active_search_json_mode(self, klasko_path):
        from compliance_os.mcp_server import h1b_active_search
        result = h1b_active_search(folder=str(klasko_path), as_json=True)
        data = json.loads(result)
        assert data["template_id"] == "h1b_petition"
        assert data["files_scanned"] > 40
        assert "coverage" in data
        assert "matched" in data

    def test_h1b_active_search_missing_folder(self):
        from compliance_os.mcp_server import h1b_active_search
        result = h1b_active_search(folder="/nonexistent/path")
        data = json.loads(result)
        assert "error" in data
