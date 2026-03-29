#!/usr/bin/env python3
"""Seed a dashboard user in Postgres from a local SQLite corpus."""
from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from pathlib import Path, PurePosixPath

from sqlalchemy import create_engine, text


def _uuid() -> str:
    return str(uuid.uuid4())


def _normalize_pg_url(url: str) -> str:
    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = "postgresql://" + normalized[len("postgres://") :]
    if normalized.startswith("postgresql://"):
        normalized = "postgresql+psycopg://" + normalized[len("postgresql://") :]
    return normalized


def _json_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _bool_or_none(value):
    if value is None:
        return None
    return bool(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sqlite", required=True, help="Path to the local SQLite db.")
    parser.add_argument("--dest-url", required=True, help="Destination Postgres URL.")
    parser.add_argument("--target-email", required=True, help="Existing user email in destination db.")
    parser.add_argument(
        "--remote-upload-root",
        default="/data/uploads/imported",
        help="Remote persistent root for copied files on Fly.",
    )
    parser.add_argument(
        "--manifest-path",
        required=True,
        help="Where to write the JSON file-copy manifest.",
    )
    parser.add_argument(
        "--replace-target-data",
        action="store_true",
        help="Delete the target user's existing checks before seeding.",
    )
    return parser


def _delete_existing_target_checks(conn, user_id: str) -> None:
    check_ids = [
        row[0]
        for row in conn.execute(
            text("select id from checks where user_id = :user_id order by created_at, id"),
            {"user_id": user_id},
        ).fetchall()
    ]
    if not check_ids:
        return

    doc_ids = [
        row[0]
        for row in conn.execute(
            text("select id from documents_v2 where check_id = any(:check_ids)"),
            {"check_ids": check_ids},
        ).fetchall()
    ]

    if doc_ids:
        conn.execute(
            text("delete from extracted_fields where document_id = any(:doc_ids)"),
            {"doc_ids": doc_ids},
        )
        conn.execute(
            text("delete from ingestion_issues where document_id = any(:doc_ids)"),
            {"doc_ids": doc_ids},
        )
        conn.execute(
            text("delete from llm_api_usage where document_id = any(:doc_ids)"),
            {"doc_ids": doc_ids},
        )
        conn.execute(
            text("delete from documents_v2 where id = any(:doc_ids)"),
            {"doc_ids": doc_ids},
        )

    conn.execute(
        text("delete from llm_api_usage where check_id = any(:check_ids)"),
        {"check_ids": check_ids},
    )
    conn.execute(
        text("delete from ingestion_issues where check_id = any(:check_ids)"),
        {"check_ids": check_ids},
    )
    conn.execute(
        text("delete from findings where check_id = any(:check_ids)"),
        {"check_ids": check_ids},
    )
    conn.execute(
        text("delete from followups where check_id = any(:check_ids)"),
        {"check_ids": check_ids},
    )
    conn.execute(
        text("delete from comparisons where check_id = any(:check_ids)"),
        {"check_ids": check_ids},
    )
    conn.execute(
        text("delete from checks where id = any(:check_ids)"),
        {"check_ids": check_ids},
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    source_path = Path(args.source_sqlite).expanduser().resolve()
    if not source_path.exists():
        raise SystemExit(f"Source SQLite db not found: {source_path}")

    manifest_path = Path(args.manifest_path).expanduser().resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    sqlite_conn = sqlite3.connect(str(source_path))
    sqlite_conn.row_factory = sqlite3.Row

    dest_engine = create_engine(_normalize_pg_url(args.dest_url), pool_pre_ping=True)

    manifest: list[dict] = []

    with dest_engine.begin() as dest_conn:
        target_user_id = dest_conn.execute(
            text("select id from users where email = :email"),
            {"email": args.target_email},
        ).scalar_one_or_none()
        if not target_user_id:
            raise SystemExit(f"Destination user not found: {args.target_email}")

        existing = dest_conn.execute(
            text("select count(*) from checks where user_id = :user_id"),
            {"user_id": target_user_id},
        ).scalar_one()
        if existing and not args.replace_target_data:
            raise SystemExit(
                f"Target user already has {existing} checks. Re-run with --replace-target-data."
            )
        if existing and args.replace_target_data:
            _delete_existing_target_checks(dest_conn, target_user_id)

        check_rows = sqlite_conn.execute(
            """
            select id, track, stage, status, answers, created_at, updated_at
            from checks
            order by created_at, id
            """
        ).fetchall()

        total_docs = 0
        total_fields = 0
        total_comparisons = 0
        total_findings = 0
        total_followups = 0
        total_issues = 0
        total_llm_usage = 0

        for check in check_rows:
            new_check_id = _uuid()
            dest_conn.execute(
                text(
                    """
                    insert into checks (id, track, stage, status, answers, user_id, created_at, updated_at)
                    values (:id, :track, :stage, :status, CAST(:answers AS json), :user_id, :created_at, :updated_at)
                    """
                ),
                {
                    "id": new_check_id,
                    "track": check["track"],
                    "stage": check["stage"],
                    "status": check["status"],
                    "answers": _json_text(check["answers"] or "{}"),
                    "user_id": target_user_id,
                    "created_at": check["created_at"],
                    "updated_at": check["updated_at"],
                },
            )

            docs = sqlite_conn.execute(
                "select * from documents_v2 where check_id = ? order by uploaded_at, id",
                (check["id"],),
            ).fetchall()
            doc_id_map: dict[str, str] = {}
            supersede_map: dict[str, str | None] = {}
            for doc in docs:
                new_doc_id = _uuid()
                doc_id_map[doc["id"]] = new_doc_id
                supersede_map[new_doc_id] = doc["supersedes_document_id"]
                src_path = Path(doc["file_path"])
                remote_dir = PurePosixPath(args.remote_upload_root) / new_check_id
                remote_path = str(remote_dir / src_path.name)
                manifest.append(
                    {
                        "source_path": str(src_path),
                        "remote_path": remote_path,
                        "check_id": new_check_id,
                        "document_id": new_doc_id,
                        "filename": doc["filename"],
                        "doc_type": doc["doc_type"],
                    }
                )
                dest_conn.execute(
                    text(
                        """
                        insert into documents_v2 (
                            id, check_id, doc_type, document_family, document_series_key, document_version,
                            supersedes_document_id, is_active, filename, source_path, file_path, file_size,
                            mime_type, content_hash, ocr_text, ocr_engine, provenance, uploaded_at
                        ) values (
                            :id, :check_id, :doc_type, :document_family, :document_series_key, :document_version,
                            null, :is_active, :filename, :source_path, :file_path, :file_size,
                            :mime_type, :content_hash, :ocr_text, :ocr_engine, CAST(:provenance AS json), :uploaded_at
                        )
                        """
                    ),
                    {
                        "id": new_doc_id,
                        "check_id": new_check_id,
                        "doc_type": doc["doc_type"],
                        "document_family": doc["document_family"],
                        "document_series_key": doc["document_series_key"],
                        "document_version": doc["document_version"],
                        "is_active": _bool_or_none(doc["is_active"]),
                        "filename": doc["filename"],
                        "source_path": doc["source_path"],
                        "file_path": remote_path,
                        "file_size": doc["file_size"],
                        "mime_type": doc["mime_type"],
                        "content_hash": doc["content_hash"],
                        "ocr_text": doc["ocr_text"],
                        "ocr_engine": doc["ocr_engine"],
                        "provenance": _json_text(doc["provenance"]),
                        "uploaded_at": doc["uploaded_at"],
                    },
                )
                total_docs += 1

                fields = sqlite_conn.execute(
                    "select * from extracted_fields where document_id = ? order by id",
                    (doc["id"],),
                ).fetchall()
                for field in fields:
                    dest_conn.execute(
                        text(
                            """
                            insert into extracted_fields (id, document_id, field_name, field_value, confidence, raw_text)
                            values (:id, :document_id, :field_name, :field_value, :confidence, :raw_text)
                            """
                        ),
                        {
                            "id": _uuid(),
                            "document_id": new_doc_id,
                            "field_name": field["field_name"],
                            "field_value": field["field_value"],
                            "confidence": field["confidence"],
                            "raw_text": field["raw_text"],
                        },
                    )
                    total_fields += 1

                doc_issues = sqlite_conn.execute(
                    "select * from ingestion_issues where document_id = ? order by detected_at, id",
                    (doc["id"],),
                ).fetchall()
                for issue in doc_issues:
                    dest_conn.execute(
                        text(
                            """
                            insert into ingestion_issues (
                                id, check_id, document_id, stage, issue_code, severity, message, details, detected_at
                            ) values (
                                :id, :check_id, :document_id, :stage, :issue_code, :severity, :message, CAST(:details AS json), :detected_at
                            )
                            """
                        ),
                        {
                            "id": _uuid(),
                            "check_id": new_check_id,
                            "document_id": new_doc_id,
                            "stage": issue["stage"],
                            "issue_code": issue["issue_code"],
                            "severity": issue["severity"],
                            "message": issue["message"],
                            "details": _json_text(issue["details"]),
                            "detected_at": issue["detected_at"],
                        },
                    )
                    total_issues += 1

                llm_usage = sqlite_conn.execute(
                    "select * from llm_api_usage where document_id = ? order by started_at, id",
                    (doc["id"],),
                ).fetchall()
                for usage in llm_usage:
                    dest_conn.execute(
                        text(
                            """
                            insert into llm_api_usage (
                                id, check_id, document_id, user_id, environment, provider, model, operation, status,
                                input_tokens, output_tokens, total_tokens, cache_creation_input_tokens,
                                cache_read_input_tokens, latency_ms, error_type, error_message,
                                request_metadata, usage_details, started_at, completed_at
                            ) values (
                                :id, :check_id, :document_id, :user_id, :environment, :provider, :model, :operation, :status,
                                :input_tokens, :output_tokens, :total_tokens, :cache_creation_input_tokens,
                                :cache_read_input_tokens, :latency_ms, :error_type, :error_message,
                                CAST(:request_metadata AS json), CAST(:usage_details AS json), :started_at, :completed_at
                            )
                            """
                        ),
                        {
                            "id": _uuid(),
                            "check_id": new_check_id,
                            "document_id": new_doc_id,
                            "user_id": target_user_id,
                            "environment": usage["environment"],
                            "provider": usage["provider"],
                            "model": usage["model"],
                            "operation": usage["operation"],
                            "status": usage["status"],
                            "input_tokens": usage["input_tokens"],
                            "output_tokens": usage["output_tokens"],
                            "total_tokens": usage["total_tokens"],
                            "cache_creation_input_tokens": usage["cache_creation_input_tokens"],
                            "cache_read_input_tokens": usage["cache_read_input_tokens"],
                            "latency_ms": usage["latency_ms"],
                            "error_type": usage["error_type"],
                            "error_message": usage["error_message"],
                            "request_metadata": _json_text(usage["request_metadata"]),
                            "usage_details": _json_text(usage["usage_details"]),
                            "started_at": usage["started_at"],
                            "completed_at": usage["completed_at"],
                        },
                    )
                    total_llm_usage += 1

            for new_doc_id, old_supersedes in supersede_map.items():
                if old_supersedes and old_supersedes in doc_id_map:
                    dest_conn.execute(
                        text(
                            "update documents_v2 set supersedes_document_id = :supersedes where id = :id"
                        ),
                        {"id": new_doc_id, "supersedes": doc_id_map[old_supersedes]},
                    )

            comparison_rows = sqlite_conn.execute(
                "select * from comparisons where check_id = ? order by id",
                (check["id"],),
            ).fetchall()
            comparison_id_map: dict[str, str] = {}
            for row in comparison_rows:
                new_id = _uuid()
                comparison_id_map[row["id"]] = new_id
                dest_conn.execute(
                    text(
                        """
                        insert into comparisons (
                            id, check_id, field_name, value_a, value_b, match_type, status, confidence, detail
                        ) values (
                            :id, :check_id, :field_name, :value_a, :value_b, :match_type, :status, :confidence, :detail
                        )
                        """
                    ),
                    {
                        "id": new_id,
                        "check_id": new_check_id,
                        "field_name": row["field_name"],
                        "value_a": row["value_a"],
                        "value_b": row["value_b"],
                        "match_type": row["match_type"],
                        "status": row["status"],
                        "confidence": row["confidence"],
                        "detail": row["detail"],
                    },
                )
                total_comparisons += 1

            followup_rows = sqlite_conn.execute(
                "select * from followups where check_id = ? order by id",
                (check["id"],),
            ).fetchall()
            for row in followup_rows:
                dest_conn.execute(
                    text(
                        """
                        insert into followups (id, check_id, question_key, question_text, chips, answer, answered_at)
                        values (:id, :check_id, :question_key, :question_text, CAST(:chips AS json), :answer, :answered_at)
                        """
                    ),
                    {
                        "id": _uuid(),
                        "check_id": new_check_id,
                        "question_key": row["question_key"],
                        "question_text": row["question_text"],
                        "chips": _json_text(row["chips"]),
                        "answer": row["answer"],
                        "answered_at": row["answered_at"],
                    },
                )
                total_followups += 1

            finding_rows = sqlite_conn.execute(
                "select * from findings where check_id = ? order by id",
                (check["id"],),
            ).fetchall()
            for row in finding_rows:
                dest_conn.execute(
                    text(
                        """
                        insert into findings (
                            id, check_id, rule_id, rule_version, severity, category, title, action,
                            consequence, immigration_impact, source_comparison_id
                        ) values (
                            :id, :check_id, :rule_id, :rule_version, :severity, :category, :title, :action,
                            :consequence, :immigration_impact, :source_comparison_id
                        )
                        """
                    ),
                    {
                        "id": _uuid(),
                        "check_id": new_check_id,
                        "rule_id": row["rule_id"],
                        "rule_version": row["rule_version"],
                        "severity": row["severity"],
                        "category": row["category"],
                        "title": row["title"],
                        "action": row["action"],
                        "consequence": row["consequence"],
                        "immigration_impact": _bool_or_none(row["immigration_impact"]),
                        "source_comparison_id": comparison_id_map.get(row["source_comparison_id"]),
                    },
                )
                total_findings += 1

            check_issues = sqlite_conn.execute(
                """
                select * from ingestion_issues
                where check_id = ? and document_id is null
                order by detected_at, id
                """,
                (check["id"],),
            ).fetchall()
            for issue in check_issues:
                dest_conn.execute(
                    text(
                        """
                        insert into ingestion_issues (
                            id, check_id, document_id, stage, issue_code, severity, message, details, detected_at
                        ) values (
                            :id, :check_id, null, :stage, :issue_code, :severity, :message, CAST(:details AS json), :detected_at
                        )
                        """
                    ),
                    {
                        "id": _uuid(),
                        "check_id": new_check_id,
                        "stage": issue["stage"],
                        "issue_code": issue["issue_code"],
                        "severity": issue["severity"],
                        "message": issue["message"],
                        "details": _json_text(issue["details"]),
                        "detected_at": issue["detected_at"],
                    },
                )
                total_issues += 1

            check_llm_usage = sqlite_conn.execute(
                """
                select * from llm_api_usage
                where check_id = ? and document_id is null
                order by started_at, id
                """,
                (check["id"],),
            ).fetchall()
            for usage in check_llm_usage:
                dest_conn.execute(
                    text(
                        """
                        insert into llm_api_usage (
                            id, check_id, document_id, user_id, environment, provider, model, operation, status,
                            input_tokens, output_tokens, total_tokens, cache_creation_input_tokens,
                            cache_read_input_tokens, latency_ms, error_type, error_message,
                            request_metadata, usage_details, started_at, completed_at
                        ) values (
                            :id, :check_id, null, :user_id, :environment, :provider, :model, :operation, :status,
                            :input_tokens, :output_tokens, :total_tokens, :cache_creation_input_tokens,
                            :cache_read_input_tokens, :latency_ms, :error_type, :error_message,
                            CAST(:request_metadata AS json), CAST(:usage_details AS json), :started_at, :completed_at
                        )
                        """
                    ),
                    {
                        "id": _uuid(),
                        "check_id": new_check_id,
                        "user_id": target_user_id,
                        "environment": usage["environment"],
                        "provider": usage["provider"],
                        "model": usage["model"],
                        "operation": usage["operation"],
                        "status": usage["status"],
                        "input_tokens": usage["input_tokens"],
                        "output_tokens": usage["output_tokens"],
                        "total_tokens": usage["total_tokens"],
                        "cache_creation_input_tokens": usage["cache_creation_input_tokens"],
                        "cache_read_input_tokens": usage["cache_read_input_tokens"],
                        "latency_ms": usage["latency_ms"],
                        "error_type": usage["error_type"],
                        "error_message": usage["error_message"],
                        "request_metadata": _json_text(usage["request_metadata"]),
                        "usage_details": _json_text(usage["usage_details"]),
                        "started_at": usage["started_at"],
                        "completed_at": usage["completed_at"],
                    },
                )
                total_llm_usage += 1

        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "checks": len(check_rows),
                    "documents": total_docs,
                    "extracted_fields": total_fields,
                    "comparisons": total_comparisons,
                    "findings": total_findings,
                    "followups": total_followups,
                    "ingestion_issues": total_issues,
                    "llm_api_usage": total_llm_usage,
                    "manifest_path": str(manifest_path),
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
