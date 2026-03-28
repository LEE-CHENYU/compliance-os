"""SQLAlchemy database setup for compliance copilot."""

from pathlib import Path

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import os
DATA_DIR = Path(os.environ.get("DATA_DIR", str(Path(__file__).parents[3] / "data")))


class Base(DeclarativeBase):
    pass


def create_engine_and_tables(db_path: str | None = None) -> Engine:
    """Create SQLite engine and all tables."""
    if db_path is None:
        DATA_DIR.mkdir(exist_ok=True)
        db_path = str(DATA_DIR / "copilot.db")
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    from compliance_os.web.models.tables import CaseRow, DiscoveryAnswerRow, ChatMessageRow, DocumentRow  # noqa: F401
    Base.metadata.create_all(engine)
    # Guardian check flow tables (v2)
    from compliance_os.web.models.tables_v2 import Base as BaseV2  # noqa: F401
    BaseV2.metadata.create_all(engine)
    _ensure_v2_columns(engine)
    return engine


def _ensure_v2_columns(engine: Engine) -> None:
    """Add newly introduced SQLite columns for the v2 document store."""
    inspector = inspect(engine)
    if "documents_v2" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("documents_v2")}
    wanted = {
        "document_family": "TEXT",
        "document_series_key": "TEXT",
        "document_version": "INTEGER DEFAULT 1",
        "supersedes_document_id": "TEXT",
        "is_active": "BOOLEAN DEFAULT 1",
        "source_path": "TEXT",
        "content_hash": "TEXT",
        "ocr_text": "TEXT",
        "ocr_engine": "TEXT",
        "provenance": "JSON",
    }

    with engine.begin() as conn:
        for name, ddl in wanted.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE documents_v2 ADD COLUMN {name} {ddl}"))

        conn.execute(text("UPDATE documents_v2 SET document_family = COALESCE(document_family, doc_type)"))
        conn.execute(text("UPDATE documents_v2 SET document_version = COALESCE(document_version, 1)"))
        conn.execute(text("UPDATE documents_v2 SET is_active = COALESCE(is_active, 1)"))
        conn.execute(text("UPDATE documents_v2 SET source_path = COALESCE(source_path, filename)"))
        _repair_v2_document_lineage(conn)


def _repair_v2_document_lineage(conn) -> None:
    """Normalize document lineage so versions are scoped per check + series key."""
    from compliance_os.web.services.document_store import (
        document_family_for_type,
        infer_document_series_key,
    )

    rows = conn.execute(
        text(
            """
            SELECT id, check_id, doc_type, source_path, filename, content_hash
            FROM documents_v2
            ORDER BY check_id, doc_type, uploaded_at, id
            """
        )
    ).mappings().all()

    groups: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        doc_type = row["doc_type"]
        series_key = infer_document_series_key(
            doc_type,
            source_path=row["source_path"],
            filename=row["filename"],
        )
        groups.setdefault((row["check_id"], doc_type, series_key), []).append(dict(row, document_series_key=series_key))

    for (_, doc_type, series_key), group_rows in groups.items():
        previous_distinct_id: str | None = None
        previous_distinct_hash: str | None = None
        previous_version = 0

        for row in group_rows:
            content_hash = row["content_hash"]
            is_duplicate = bool(
                previous_distinct_id
                and content_hash
                and previous_distinct_hash
                and content_hash == previous_distinct_hash
            )

            if is_duplicate:
                version = previous_version
                supersedes = previous_distinct_id
                is_active = 0
            else:
                version = previous_version + 1
                supersedes = previous_distinct_id
                is_active = 1
                if previous_distinct_id is not None:
                    conn.execute(
                        text("UPDATE documents_v2 SET is_active = 0 WHERE id = :id"),
                        {"id": previous_distinct_id},
                    )
                previous_distinct_id = row["id"]
                previous_distinct_hash = content_hash
                previous_version = version

            conn.execute(
                text(
                    """
                    UPDATE documents_v2
                    SET document_family = :document_family,
                        document_series_key = :document_series_key,
                        document_version = :document_version,
                        supersedes_document_id = :supersedes_document_id,
                        is_active = :is_active
                    WHERE id = :id
                    """
                ),
                {
                    "id": row["id"],
                    "document_family": document_family_for_type(doc_type),
                    "document_series_key": series_key,
                    "document_version": version,
                    "supersedes_document_id": supersedes,
                    "is_active": is_active,
                },
            )


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine_and_tables()
    return _engine


def get_session():
    """Yield a SQLAlchemy session (for FastAPI Depends)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()
