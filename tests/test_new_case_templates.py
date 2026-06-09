"""The 4 new generic case templates resolve and are structurally sound."""

import pytest

from compliance_os.case_templates.validator import resolve_template


@pytest.mark.parametrize("alias,template_id,sections", [
    ("founder_h1b", "founder_h1b_petition", {"A", "B", "C", "D", "E", "F"}),
    ("form_5472", "form_5472_dre", {"0", "1", "2", "3", "4"}),
    ("eb1a", "eb1a_evidence", {"0", "1", "2", "3", "4", "5", "6", "7", "8"}),
    ("dependent_status", "dependent_status", {"A", "B", "C", "D"}),
])
def test_new_template_resolves_and_is_sound(alias, template_id, sections):
    tpl = resolve_template(alias)
    assert tpl.id == template_id
    assert set(tpl.sections.keys()) == sections
    ids = [s.id for s in tpl.slots]
    assert len(ids) == len(set(ids)), "slot ids must be unique"
    assert len(tpl.slots) >= 5
    for s in tpl.slots:
        assert s.section in tpl.sections, f"slot {s.id} references undeclared section {s.section}"
    # the full template id alias resolves too
    assert resolve_template(template_id).id == template_id
