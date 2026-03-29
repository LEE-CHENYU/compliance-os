from __future__ import annotations

import hashlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import Base as OldBase
from compliance_os.web.models.tables_v2 import Base as BaseV2, CheckRow, DocumentRow
import compliance_os.web.services.legacy_document_repair as repair_mod
from compliance_os.web.services.document_intake import ResolvedDocumentType


def test_repair_user_documents_backfills_hash_reclassifies_and_normalizes_source(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    OldBase.metadata.create_all(engine)
    BaseV2.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    file_bytes = b"same-content"
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    canonical_path = tmp_path / "canonical.pdf"
    legacy_path = tmp_path / "legacy.pdf"
    canonical_path.write_bytes(file_bytes)
    legacy_path.write_bytes(file_bytes)

    session = SessionLocal()
    user = UserRow(email="repair@example.com", password_hash="x")
    session.add(user)
    session.flush()

    check_one = CheckRow(track="stem_opt", status="reviewed", user_id=user.id, answers={})
    check_two = CheckRow(track="stem_opt", status="reviewed", user_id=user.id, answers={})
    session.add_all([check_one, check_two])
    session.flush()

    canonical_doc = DocumentRow(
        check_id=check_one.id,
        doc_type="employment_letter",
        filename="Wolff_&_Li_Capital_Offer_Letter.pdf",
        file_path=str(canonical_path),
        file_size=len(file_bytes),
        mime_type="application/pdf",
        content_hash=content_hash,
        source_path="/Users/lichenyu/Desktop/Important Docs /Employment/Wolff_&_Li_Capital_Offer_Letter.pdf",
    )
    legacy_doc = DocumentRow(
        check_id=check_two.id,
        doc_type="i983",
        filename="Wolff_&_Li_Capital_Offer_Letter.pdf",
        file_path=str(legacy_path),
        file_size=len(file_bytes),
        mime_type="application/pdf",
        content_hash=None,
        source_path="Wolff_&_Li_Capital_Offer_Letter.pdf",
    )
    session.add_all([canonical_doc, legacy_doc])
    session.commit()

    monkeypatch.setattr(
        repair_mod,
        "resolve_document_type",
        lambda file_path, mime_type, *, provided_doc_type=None, allow_ocr=False: ResolvedDocumentType(
            doc_type="employment_letter",
            confidence="high",
            source="filename",
            provided_doc_type=provided_doc_type,
        ),
    )
    reextracted: list[str] = []
    monkeypatch.setattr(
        repair_mod,
        "extract_into_document",
        lambda doc, db: reextracted.append(doc.id) or {"document_id": doc.id},
    )

    result = repair_mod.repair_user_documents(
        session,
        email="repair@example.com",
        apply_changes=True,
        reextract_changed=True,
    )

    refreshed = session.get(DocumentRow, legacy_doc.id)
    assert refreshed.content_hash == content_hash
    assert refreshed.doc_type == "employment_letter"
    assert refreshed.source_path == canonical_doc.source_path
    assert result["summary"]["hash_backfilled"] == 1
    assert result["summary"]["source_path_normalized"] == 1
    assert result["summary"]["doc_type_reclassified"] == 1
    assert result["summary"]["reextracted_documents"] == 1
    assert reextracted == [legacy_doc.id]

    session.close()
