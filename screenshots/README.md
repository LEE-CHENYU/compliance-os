# Screenshots

Organized snapshots of the app UI, marketing pages, and ad-hoc captures.
The repo root used to accumulate loose `.png` files; now they live here
by purpose.

## Subfolders

- `eval/` — UI captures produced by the pipeline rubric runs
  (`docs/pipeline_eval_*.md`). Local dashboard, prod dashboard,
  deadlines view, key-facts view.
- `marketing/` — share-page, brand assets, mobile before/after,
  integrations section. Referenced from `docs/connector-submission.md`.
- `debug/` — one-off captures of prod issues; keep around as
  evidence on incident reports.

## Naming

`<surface>-<state>.png` (e.g., `local-dashboard.png`,
`prod-cl4183-deadlines.png`, `mobile-after.png`). Avoid timestamps in
the filename — overwrite the previous capture so a doc that links to
`screenshots/eval/local-dashboard.png` keeps showing the current state
of that surface. If you need to preserve a specific moment, drop a
copy under `debug/` with a date.
