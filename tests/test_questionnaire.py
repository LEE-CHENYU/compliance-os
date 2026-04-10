"""Tests for the marketplace questionnaire engine."""

from compliance_os.web.services.questionnaire import evaluate


def test_questionnaire_routes_to_execution():
    result = evaluate(
        "opt_execution",
        {
            "f1_good_standing": True,
            "full_time_enrolled": True,
            "employment_plan": True,
            "school_confirmed_eligible": True,
            "has_i20": True,
            "has_passport": True,
            "has_photos": True,
            "denied_before": False,
            "prior_rfe": False,
            "unauthorized_employment": False,
            "late_application": False,
        },
    )
    assert result.recommendation == "execution"
    assert result.advisory_reason is None
    assert result.execution_reason


def test_questionnaire_routes_to_advisory_on_complexity_flag():
    result = evaluate(
        "opt_execution",
        {
            "f1_good_standing": True,
            "full_time_enrolled": True,
            "employment_plan": True,
            "school_confirmed_eligible": True,
            "has_i20": True,
            "has_passport": True,
            "has_photos": True,
            "denied_before": True,
            "prior_rfe": False,
            "unauthorized_employment": False,
            "late_application": False,
        },
    )
    assert result.recommendation == "advisory"
    assert "denied" in (result.advisory_reason or "").lower()
