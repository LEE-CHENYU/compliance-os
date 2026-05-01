# Document-pipeline eval rubric (v1)

This rubric scores the end-to-end pipeline that turns a file on disk into
something useful in the user-facing data room: ingest → classify →
upload → index → finding/deadline extraction → render on the website.

It is run against `tests/fixtures/accounting_eval_set/manifest.yaml`,
which is the labeled fixture pulled from `/Users/lichenyu/accounting`.
Every dimension is tied to a manifest entry or a known seeded doc, so a
score is reproducible across pipeline changes — re-running after a
classifier change tells you which dimensions improved and which
regressed.

## Dimensions

| # | Dimension | Method | Pass bar | Automatable |
|---|-----------|--------|----------|-------------|
| 1 | **Ingest reliability** | `batch_upload` over the fixture; count non-2xx responses | ≥98% complete without 4xx/5xx | yes |
| 2 | **Classification accuracy** | confusion matrix vs `manifest.yaml.expected_doc_type` | ≥85% top-1 match (per category and overall) | yes |
| 3 | **Dedup correctness** | re-upload the same fixture, count `duplicate_detected` responses | 100% (zero re-ingestion) | yes |
| 4 | **Index coverage** | for each uploaded doc, query the document store with a unique phrase derived from the filename or first-page text | ≥95% retrievable within 60s | yes |
| 5 | **Finding extraction** | seed 5 known-risk docs (expired I-20, missed deadline, foreign-source wire, etc.); inspect `/findings` after upload | 5/5 surfaced within 10 min | manual |
| 6 | **Deadline detection** | seed 5 dated docs; inspect `/deadlines` after upload | 5/5 with correct date | manual |
| 7 | **End-to-end latency** | per-doc time from `upload_document` POST to `query_documents` hit | p95 < 30s on local sqlite | yes |
| 8 | **Token / $ cost per 100 docs** | log API calls during the run | report; no pass bar yet, just a baseline | yes |

Negative-control entries (`expected_doc_type: null`) are scored separately
under dimension 2: the pipeline should *refuse to assign a doc_type* to
agent-generated analyses, prep notes, voice-memo transcripts. A
false-positive classification on a negative control is worse than a
false-negative on a real doc — it pollutes the data room.

## Scoring formula

```
overall = 0.20 * ingest_reliability        # dim 1, weight high — failures kill the rest
        + 0.30 * classification_accuracy   # dim 2, the headline number
        + 0.10 * dedup_correctness         # dim 3
        + 0.15 * index_coverage            # dim 4
        + 0.15 * finding_extraction        # dim 5 (manual)
        + 0.10 * deadline_detection        # dim 6 (manual)
                                           # dim 7, 8 are reported but unweighted
```

A failing classification accuracy (<85%) blocks Phase 2 dogfooding
regardless of the weighted overall — wrongly-typed docs in the user's
real data room are worse than no docs at all.

## Outputs

The eval runner emits two artifacts per run:

1. `docs/pipeline_eval_<YYYY-MM-DD>.md` — human-readable report with
   per-dimension scores, the confusion matrix for dim 2, and a gap
   list with severity.
2. `docs/pipeline_eval_<YYYY-MM-DD>.json` — machine-readable scores so
   CI / future runs can detect regressions.

## Running

```bash
conda activate compliance-os
python scripts/run_pipeline_eval.py \
  --manifest tests/fixtures/accounting_eval_set/manifest.yaml \
  --user-email eval-20260430@guardian.local \
  --api-url http://127.0.0.1:8000
```

Re-running on the same user is a no-op for ingest (dedup) but always
re-scores dimensions 2 and 4.

## What this rubric is not

- Not a measure of *user value*. We can hit 95% accuracy and still build
  the wrong thing. Phase 2 (cl4183 dogfood) is the sanity check on
  whether the data room is useful — that's a qualitative read, not
  this rubric.
- Not a regression test. It's an eval: a snapshot of pipeline quality
  on a known fixture. Real CI tests would be unit-level (per regex,
  per parser).
- Not a substitute for production telemetry. Ingest reliability on a
  curated fixture is a ceiling, not a floor.
