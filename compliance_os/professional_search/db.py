"""Diligence DB — SQLite-backed professional-vendor tracking.

Ported from /Users/lichenyu/accounting/scripts/diligence_db.py, with the
DB path resolved from compliance-os settings instead of the script's
project root. The upsert helpers are unchanged.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Optional

from compliance_os.settings import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _db_path() -> Path:
    override = getattr(settings, "diligence_db_path", None)
    if override:
        return Path(override)
    return settings.project_root / "data" / "diligence.db"


@contextmanager
def connect(db_path: Optional[Path] = None):
    """Open a connection with FK on; commit on clean exit, rollback on error."""
    path = Path(db_path) if db_path else _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(db_path: Optional[Path] = None) -> Path:
    """Apply schema.sql. Safe to run repeatedly. Returns the DB path used."""
    schema_sql = SCHEMA_PATH.read_text()
    path = Path(db_path) if db_path else _db_path()
    with connect(path) as conn:
        conn.executescript(schema_sql)
    return path


# ----------------------------- upserts ------------------------------

def upsert_vendor(conn: sqlite3.Connection, **fields: Any) -> int:
    """Insert or update a vendor by name; returns vendor id."""
    name = fields["name"]
    row = conn.execute("SELECT id FROM vendors WHERE name = ?", (name,)).fetchone()
    if row:
        vid = row["id"]
        cols = [c for c in fields if c != "name"]
        if cols:
            sets = ", ".join(f"{c} = :{c}" for c in cols)
            conn.execute(
                f"UPDATE vendors SET {sets} WHERE id = :id",
                {**fields, "id": vid},
            )
        return vid
    cols = list(fields)
    placeholders = ", ".join(f":{c}" for c in cols)
    cur = conn.execute(
        f"INSERT INTO vendors ({', '.join(cols)}) VALUES ({placeholders})",
        fields,
    )
    return cur.lastrowid


def upsert_contact(conn: sqlite3.Connection, vendor_id: int, **fields: Any) -> int:
    name = fields["name"]
    row = conn.execute(
        "SELECT id FROM contacts WHERE vendor_id = ? AND name = ?",
        (vendor_id, name),
    ).fetchone()
    fields = {**fields, "vendor_id": vendor_id}
    if row:
        cid = row["id"]
        cols = [c for c in fields if c not in ("name", "vendor_id")]
        if cols:
            sets = ", ".join(f"{c} = :{c}" for c in cols)
            conn.execute(
                f"UPDATE contacts SET {sets} WHERE id = :id",
                {**fields, "id": cid},
            )
        return cid
    cols = list(fields)
    placeholders = ", ".join(f":{c}" for c in cols)
    cur = conn.execute(
        f"INSERT INTO contacts ({', '.join(cols)}) VALUES ({placeholders})",
        fields,
    )
    return cur.lastrowid


def upsert_engagement(conn: sqlite3.Connection, vendor_id: int, **fields: Any) -> int:
    purpose = fields["purpose"]
    row = conn.execute(
        "SELECT id FROM engagements WHERE vendor_id = ? AND purpose = ?",
        (vendor_id, purpose),
    ).fetchone()
    fields = {**fields, "vendor_id": vendor_id}
    if row:
        eid = row["id"]
        cols = [c for c in fields if c not in ("purpose", "vendor_id")]
        if cols:
            sets = ", ".join(f"{c} = :{c}" for c in cols)
            conn.execute(
                f"UPDATE engagements SET {sets} WHERE id = :id",
                {**fields, "id": eid},
            )
        return eid
    cols = list(fields)
    placeholders = ", ".join(f":{c}" for c in cols)
    cur = conn.execute(
        f"INSERT INTO engagements ({', '.join(cols)}) VALUES ({placeholders})",
        fields,
    )
    return cur.lastrowid


def add_quote(conn: sqlite3.Connection, engagement_id: int, **fields: Any) -> int:
    """Insert a quote with crude dedup on (engagement, service, amount_low, date)."""
    fields = {**fields, "engagement_id": engagement_id}
    row = conn.execute(
        """SELECT id FROM quotes
           WHERE engagement_id = ? AND service = ?
             AND COALESCE(amount_low,-1) = COALESCE(?,-1)
             AND COALESCE(quote_date,'') = COALESCE(?,'')""",
        (
            engagement_id,
            fields["service"],
            fields.get("amount_low"),
            fields.get("quote_date"),
        ),
    ).fetchone()
    if row:
        return row["id"]
    cols = list(fields)
    placeholders = ", ".join(f":{c}" for c in cols)
    cur = conn.execute(
        f"INSERT INTO quotes ({', '.join(cols)}) VALUES ({placeholders})",
        fields,
    )
    return cur.lastrowid


def add_evaluation(conn: sqlite3.Connection, engagement_id: int, **fields: Any) -> int:
    fields = {**fields, "engagement_id": engagement_id}
    row = conn.execute(
        "SELECT id FROM evaluations WHERE engagement_id = ? AND criterion = ?",
        (engagement_id, fields["criterion"]),
    ).fetchone()
    if row:
        eid = row["id"]
        cols = [c for c in fields if c not in ("criterion", "engagement_id")]
        if cols:
            sets = ", ".join(f"{c} = :{c}" for c in cols)
            conn.execute(
                f"UPDATE evaluations SET {sets} WHERE id = :id",
                {**fields, "id": eid},
            )
        return eid
    cols = list(fields)
    placeholders = ", ".join(f":{c}" for c in cols)
    cur = conn.execute(
        f"INSERT INTO evaluations ({', '.join(cols)}) VALUES ({placeholders})",
        fields,
    )
    return cur.lastrowid


def add_risk(conn: sqlite3.Connection, engagement_id: int, **fields: Any) -> int:
    fields = {**fields, "engagement_id": engagement_id}
    row = conn.execute(
        "SELECT id FROM risks WHERE engagement_id = ? AND risk = ?",
        (engagement_id, fields["risk"]),
    ).fetchone()
    if row:
        rid = row["id"]
        cols = [c for c in fields if c not in ("risk", "engagement_id")]
        if cols:
            sets = ", ".join(f"{c} = :{c}" for c in cols)
            conn.execute(
                f"UPDATE risks SET {sets} WHERE id = :id",
                {**fields, "id": rid},
            )
        return rid
    cols = list(fields)
    placeholders = ", ".join(f":{c}" for c in cols)
    cur = conn.execute(
        f"INSERT INTO risks ({', '.join(cols)}) VALUES ({placeholders})",
        fields,
    )
    return cur.lastrowid


def add_interaction(conn: sqlite3.Connection, engagement_id: int, **fields: Any) -> int:
    fields = {**fields, "engagement_id": engagement_id}
    if fields.get("reference_id"):
        row = conn.execute(
            "SELECT id FROM interactions WHERE reference_id = ?",
            (fields["reference_id"],),
        ).fetchone()
    else:
        row = conn.execute(
            """SELECT id FROM interactions
               WHERE engagement_id = ? AND interaction_type = ?
                 AND occurred_at = ? AND COALESCE(subject,'') = COALESCE(?,'')""",
            (
                engagement_id,
                fields["interaction_type"],
                fields["occurred_at"],
                fields.get("subject"),
            ),
        ).fetchone()
    if row:
        return row["id"]
    cols = list(fields)
    placeholders = ", ".join(f":{c}" for c in cols)
    cur = conn.execute(
        f"INSERT INTO interactions ({', '.join(cols)}) VALUES ({placeholders})",
        fields,
    )
    return cur.lastrowid


def add_document(conn: sqlite3.Connection, **fields: Any) -> int:
    row = conn.execute(
        "SELECT id FROM documents WHERE file_path = ?",
        (fields["file_path"],),
    ).fetchone()
    if row:
        did = row["id"]
        cols = [c for c in fields if c != "file_path"]
        if cols:
            sets = ", ".join(f"{c} = :{c}" for c in cols)
            conn.execute(
                f"UPDATE documents SET {sets} WHERE id = :id",
                {**fields, "id": did},
            )
        return did
    cols = list(fields)
    placeholders = ", ".join(f":{c}" for c in cols)
    cur = conn.execute(
        f"INSERT INTO documents ({', '.join(cols)}) VALUES ({placeholders})",
        fields,
    )
    return cur.lastrowid


# ----------------------------- readers ------------------------------

def _rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


def attorney_comparison(conn: sqlite3.Connection) -> list[dict]:
    return _rows_to_dicts(
        conn.execute(
            "SELECT * FROM v_attorney_comparison "
            "ORDER BY score IS NULL, score DESC"
        )
    )


def vendor_comparison(
    conn: sqlite3.Connection, vendor_type: Optional[str] = None
) -> list[dict]:
    if vendor_type:
        rows = conn.execute(
            "SELECT * FROM v_vendor_comparison WHERE vendor_type = ? "
            "ORDER BY score IS NULL, score DESC",
            (vendor_type,),
        )
    else:
        rows = conn.execute(
            "SELECT * FROM v_vendor_comparison "
            "ORDER BY vendor_type, score IS NULL, score DESC"
        )
    return _rows_to_dicts(rows)


def vendor_directory(
    conn: sqlite3.Connection, vendor_type: Optional[str] = None
) -> list[dict]:
    if vendor_type:
        rows = conn.execute(
            "SELECT * FROM v_vendor_directory WHERE vendor_type = ? ORDER BY name",
            (vendor_type,),
        )
    else:
        rows = conn.execute(
            "SELECT * FROM v_vendor_directory ORDER BY vendor_type, name"
        )
    return _rows_to_dicts(rows)


def vendor_detail(conn: sqlite3.Connection, name_fragment: str) -> Optional[dict]:
    """Full dossier for one vendor (fuzzy name match)."""
    rows = conn.execute(
        "SELECT * FROM vendors WHERE name LIKE ?",
        (f"%{name_fragment}%",),
    ).fetchall()
    if not rows:
        return None
    if len(rows) > 1:
        return {
            "ambiguous": True,
            "matches": [{"name": r["name"], "vendor_type": r["vendor_type"]} for r in rows],
        }
    v = dict(rows[0])
    vid = v["id"]
    v["contacts"] = _rows_to_dicts(
        conn.execute(
            "SELECT * FROM contacts WHERE vendor_id = ? "
            "ORDER BY is_primary DESC, name",
            (vid,),
        )
    )
    engagements = _rows_to_dicts(
        conn.execute("SELECT * FROM engagements WHERE vendor_id = ?", (vid,))
    )
    for e in engagements:
        e["quotes"] = _rows_to_dicts(
            conn.execute(
                "SELECT * FROM quotes WHERE engagement_id = ? ORDER BY quote_date",
                (e["id"],),
            )
        )
        e["evaluations"] = _rows_to_dicts(
            conn.execute(
                "SELECT * FROM evaluations WHERE engagement_id = ?", (e["id"],)
            )
        )
        e["risks"] = _rows_to_dicts(
            conn.execute(
                "SELECT * FROM risks WHERE engagement_id = ? "
                "ORDER BY CASE severity "
                "  WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
                "  WHEN 'medium' THEN 2 ELSE 3 END",
                (e["id"],),
            )
        )
        e["interactions"] = _rows_to_dicts(
            conn.execute(
                "SELECT * FROM interactions WHERE engagement_id = ? "
                "ORDER BY occurred_at DESC LIMIT 10",
                (e["id"],),
            )
        )
    v["engagements"] = engagements
    return v
