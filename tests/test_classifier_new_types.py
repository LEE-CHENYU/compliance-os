"""Classifier + extraction-schema coverage for the new immigration doc types."""

from compliance_os.facts.extraction_map import schema_for_doc_type
from compliance_os.web.services.classifier import classify_text


def _classify(text):
    return classify_text(text).doc_type


def test_classify_i797():
    assert _classify("Notice of Action Form I-797C Receipt Number EAC2190012345") == "i797"


def test_classify_i130():
    assert _classify("Petition for Alien Relative Form I-130 filed by petitioner") == "i130"


def test_classify_i485():
    assert _classify("Application to Register Permanent Residence or Adjust Status Form I-485 Priority Date") == "i485"


def test_classify_lca():
    assert _classify("Labor Condition Application ETA Case Number I-200-12345 SOC Code 15-1252 Prevailing Wage Level II") == "lca"


def test_classify_ds2019():
    assert _classify("Certificate of Eligibility for Exchange Visitor (J-1) Status Form DS-2019 Program Sponsor") == "ds2019"


def test_classify_advance_parole():
    assert _classify("Advance Parole Authorization for Parole Form I-512L travel authorization") == "advance_parole"


def test_lca_schema_maps_soc_code_and_wage_number():
    by_field = {e["source_field"]: e for e in schema_for_doc_type("lca")}
    assert by_field["soc_code"]["fact_key"] == "lca_soc_code"
    assert by_field["prevailing_wage"]["shape"] == "number"


def test_advance_parole_expiry_is_own_fact_not_stem_opt():
    by_field = {e["source_field"]: e for e in schema_for_doc_type("advance_parole")}
    assert by_field["valid_to"]["fact_key"] == "advance_parole_expiry"
    assert by_field["valid_to"]["fact_key"] != "stem_opt_end_date"


def test_i485_uses_shared_priority_date_and_aos_receipt():
    by_field = {e["source_field"]: e for e in schema_for_doc_type("i485")}
    assert by_field["priority_date"]["fact_key"] == "priority_date"
    assert by_field["receipt_number"]["fact_key"] == "aos_receipt_number"
