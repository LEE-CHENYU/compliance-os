from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from compliance_os.web.models.tables_v2 import (
    Base,
    CheckRow,
    DocumentRow,
    ExtractedFieldRow,
)
from compliance_os.web.services.subject_chains import (
    list_user_subject_chains,
    serialize_subject_chain,
    sync_user_subject_chains,
)


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_sync_user_subject_chains_persists_employment_and_entity_chains(tmp_path):
    session = _session()
    now = datetime.now(timezone.utc)
    user_id = "user-1"
    try:
        stem_check = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        entity_check = CheckRow(track="entity", status="reviewed", user_id=user_id, answers={"entity_type": "smllc"})
        session.add_all([stem_check, entity_check])
        session.flush()

        wolff_old = DocumentRow(
            check_id=stem_check.id,
            doc_type="i983",
            filename="i983-wolff-and-li.pdf",
            file_path=str(tmp_path / "i983-wolff-old.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="stem opt/i983/wolff-and-li/i983-wolff-and-li.pdf",
            uploaded_at=now - timedelta(days=2),
        )
        wolff_new = DocumentRow(
            check_id=stem_check.id,
            doc_type="i983",
            filename="i983-wolff-and-li-signed.pdf",
            file_path=str(tmp_path / "i983-wolff-new.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="stem opt/i983/wolff-and-li/i983-wolff-and-li-signed.pdf",
            uploaded_at=now - timedelta(days=1),
        )
        wolff_offer = DocumentRow(
            check_id=stem_check.id,
            doc_type="employment_letter",
            filename="Wolff_&_Li_Capital_Offer_Letter.pdf",
            file_path=str(tmp_path / "offer-wolff.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="employment/Wolff & Li/Wolff_&_Li_Capital_Offer_Letter.pdf",
            uploaded_at=now,
        )
        entity_articles = DocumentRow(
            check_id=entity_check.id,
            doc_type="articles_of_organization",
            filename="Articles.pdf",
            file_path=str(tmp_path / "articles.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="entity/articles/Articles.pdf",
            uploaded_at=now - timedelta(days=10),
        )
        entity_tax = DocumentRow(
            check_id=entity_check.id,
            doc_type="tax_return",
            filename="2024_Entity_TaxReturn.pdf",
            file_path=str(tmp_path / "entity-tax.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="entity/tax/2024_Entity_TaxReturn.pdf",
            uploaded_at=now - timedelta(days=5),
        )
        session.add_all([wolff_old, wolff_new, wolff_offer, entity_articles, entity_tax])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=wolff_old.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=wolff_old.id, field_name="start_date", field_value="2024-01-23"),
                ExtractedFieldRow(document_id=wolff_old.id, field_name="end_date", field_value="2026-01-22"),
                ExtractedFieldRow(document_id=wolff_new.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=wolff_new.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=wolff_offer.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=wolff_offer.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=entity_articles.id, field_name="entity_name", field_value="Bamboo Shoot Growth Capital LLC"),
                ExtractedFieldRow(document_id=entity_tax.id, field_name="entity_name", field_value="Bamboo Shoot Growth Capital LLC"),
                ExtractedFieldRow(document_id=entity_tax.id, field_name="tax_year", field_value="2024"),
            ]
        )
        session.commit()

        sync_user_subject_chains(user_id, session)
        session.commit()

        chains = list_user_subject_chains(user_id, session)
        employment = {chain.chain_key: chain for chain in chains if chain.chain_type == "employment"}
        entity = {chain.chain_key: chain for chain in chains if chain.chain_type == "entity"}

        assert employment["employment:wolff-li-capital-inc:2024-01-23"].status == "superseded"
        assert employment["employment:wolff-li-capital-inc:2024-01-23"].snapshot["timeline_visible"] is False

        active_wolff = employment["employment:wolff-li-capital-inc:2025-03-17"]
        assert active_wolff.status == "active"
        assert active_wolff.display_name == "Wolff & Li Capital Inc."
        assert set(active_wolff.snapshot["start_document_ids"]) == {wolff_new.id, wolff_offer.id}

        bamboo = entity["entity:bamboo-shoot-growth-capital-llc"]
        assert bamboo.display_name == "Bamboo Shoot Growth Capital LLC"
        assert bamboo.snapshot["tax_events"] == [
            {
                "date": "2024-04-15",
                "title": "2024 Tax Return filed",
                "document_ids": [entity_tax.id],
            }
        ]
    finally:
        session.close()


def test_sync_user_subject_chains_absorbs_context_only_support_docs_into_named_employment_chain(tmp_path):
    session = _session()
    now = datetime.now(timezone.utc)
    user_id = "user-2"
    try:
        check = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        session.add(check)
        session.flush()

        i983 = DocumentRow(
            check_id=check.id,
            doc_type="i983",
            filename="Chenyu_i983 Form_100124_ink_signed.pdf",
            file_path=str(tmp_path / "vcv-i983.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="employment/vcv/Chenyu_i983 Form_100124_ink_signed.pdf",
            uploaded_at=now - timedelta(days=2),
        )
        i9 = DocumentRow(
            check_id=check.id,
            doc_type="i9",
            filename="I9.pdf",
            file_path=str(tmp_path / "vcv-i9.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="employment/vcv/I9.pdf",
            uploaded_at=now - timedelta(days=1),
        )
        session.add_all([i983, i9])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=i983.id, field_name="employer_name", field_value="Tiger Cloud LLC"),
                ExtractedFieldRow(document_id=i983.id, field_name="start_date", field_value="2024-10-01"),
                ExtractedFieldRow(document_id=i9.id, field_name="company_name", field_value="VCV"),
                ExtractedFieldRow(document_id=i9.id, field_name="employee_first_day_of_employment", field_value="2026-03-17"),
            ]
        )
        session.commit()

        sync_user_subject_chains(user_id, session)
        session.commit()

        chains = [chain for chain in list_user_subject_chains(user_id, session) if chain.chain_type == "employment"]
        assert [chain.chain_key for chain in chains] == ["employment:tiger-cloud-llc:2024-10-01"]
        tiger = chains[0]
        assert tiger.display_name == "Tiger Cloud LLC (vcv)"
        linked_filenames = {link.document.filename for link in tiger.document_links if link.document is not None}
        assert linked_filenames == {
            "Chenyu_i983 Form_100124_ink_signed.pdf",
            "I9.pdf",
        }
        assert set(tiger.snapshot["start_document_ids"]) == {i983.id}
    finally:
        session.close()


def test_sync_user_subject_chains_merges_identifier_only_tax_return_into_entity_chain(tmp_path):
    session = _session()
    now = datetime.now(timezone.utc)
    user_id = "user-3"
    try:
        check = CheckRow(track="entity", status="reviewed", user_id=user_id, answers={"entity_type": "smllc"})
        session.add(check)
        session.flush()

        ein_letter = DocumentRow(
            check_id=check.id,
            doc_type="ein_letter",
            filename="CP575Notice.pdf",
            file_path=str(tmp_path / "cp575.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="business/bamboo/CP575Notice.pdf",
            uploaded_at=now - timedelta(days=3),
        )
        tax_return = DocumentRow(
            check_id=check.id,
            doc_type="tax_return",
            filename="2024_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-return.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="business/bamboo/2024_TaxReturn.pdf",
            uploaded_at=now - timedelta(days=1),
        )
        session.add_all([ein_letter, tax_return])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=ein_letter.id, field_name="entity_name", field_value="Bamboo Shoot Growth Capital LLC"),
                ExtractedFieldRow(document_id=ein_letter.id, field_name="ein", field_value="10-9974443"),
                ExtractedFieldRow(document_id=tax_return.id, field_name="entity_name", field_value="2024"),
                ExtractedFieldRow(document_id=tax_return.id, field_name="ein", field_value="10-9974443"),
                ExtractedFieldRow(document_id=tax_return.id, field_name="tax_year", field_value="2024"),
            ]
        )
        session.commit()

        sync_user_subject_chains(user_id, session)
        session.commit()

        entity_chains = [chain for chain in list_user_subject_chains(user_id, session) if chain.chain_type == "entity"]
        assert [chain.chain_key for chain in entity_chains] == ["entity:bamboo-shoot-growth-capital-llc"]
        bamboo = entity_chains[0]
        assert bamboo.display_name == "Bamboo Shoot Growth Capital LLC"
        assert bamboo.snapshot["tax_events"] == [
            {
                "date": "2024-04-15",
                "title": "2024 Tax Return filed",
                "document_ids": [tax_return.id],
            }
        ]
    finally:
        session.close()


def test_serialize_subject_chain_dedupes_equivalent_documents(tmp_path):
    session = _session()
    now = datetime.now(timezone.utc)
    user_id = "user-4"
    try:
        check_one = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        check_two = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        session.add_all([check_one, check_two])
        session.flush()

        offer_one = DocumentRow(
            check_id=check_one.id,
            doc_type="employment_letter",
            filename="Wolff_&_Li_Capital_Offer_Letter.pdf",
            file_path=str(tmp_path / "offer-1.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="employment/Wolff & Li/Wolff_&_Li_Capital_Offer_Letter.pdf",
            content_hash="abcd" * 16,
            uploaded_at=now - timedelta(days=1),
        )
        offer_two = DocumentRow(
            check_id=check_two.id,
            doc_type="employment_letter",
            filename="Wolff_&_Li_Capital_Offer_Letter.pdf",
            file_path=str(tmp_path / "offer-2.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="employment/Wolff & Li/Wolff_&_Li_Capital_Offer_Letter.pdf",
            content_hash="abcd" * 16,
            uploaded_at=now,
        )
        session.add_all([offer_one, offer_two])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=offer_one.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=offer_one.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=offer_two.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=offer_two.id, field_name="start_date", field_value="2025-03-17"),
            ]
        )
        session.commit()

        sync_user_subject_chains(user_id, session)
        session.commit()

        chain = next(chain for chain in list_user_subject_chains(user_id, session) if chain.chain_type == "employment")
        serialized = serialize_subject_chain(chain)
        assert [item["filename"] for item in serialized["documents"]] == ["Wolff_&_Li_Capital_Offer_Letter.pdf"]
        assert [item["document_id"] for item in serialized["documents"]] == [offer_two.id]
    finally:
        session.close()
