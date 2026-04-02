#!/usr/bin/env python3
"""Re-extract documents that have no OCR text. Run ON the Fly machine."""
import os
import sys

sys.path.insert(0, "/app")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow
from compliance_os.web.services.document_store import extract_into_document

db_url = os.environ["DATABASE_URL"]
if "postgresql://" in db_url and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://")

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

user_id = db.execute(text("SELECT id FROM users WHERE email = 'test@123.com'")).scalar_one()

docs = (
    db.query(DocumentRow)
    .join(CheckRow)
    .filter(CheckRow.user_id == user_id, DocumentRow.ocr_text.is_(None))
    .all()
)

print(f"Found {len(docs)} docs without OCR")
success = 0
errors = 0
for doc in docs:
    try:
        label = f"[{doc.doc_type}] {doc.filename}"
        print(f"  Extracting {label}...", end=" ", flush=True)
        extract_into_document(doc, db)
        db.commit()
        field_count = len(doc.extracted_fields)
        print(f"OK ({field_count} fields)")
        success += 1
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        errors += 1

db.close()
print(f"\nDone. Success: {success}, Errors: {errors}")
