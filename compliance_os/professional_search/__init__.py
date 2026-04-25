"""Professional-search subsystem — find and track attorneys, CPAs, bankers, etc.

Two complementary modes:

- **Active search** (`personas.build_search_plan`) — three sub-agent personas
  each scout a different slice of the market (elite / startup-focused /
  litigation-focused), return structured YAML.
- **Ingest + tier report** (`ingest.ingest_docs`, `db.*`) — merge YAMLs into
  a SQLite diligence DB; query `v_attorney_comparison` for a ranked tier list.

Ported from the accounting project's `diligence_*` scripts, generalized so
that case-specific risks live in the input YAML rather than code.
"""

from compliance_os.professional_search.db import (  # noqa: F401
    connect,
    init_schema,
    upsert_vendor,
    upsert_contact,
    upsert_engagement,
    add_quote,
    add_evaluation,
    add_risk,
    add_interaction,
    add_document,
)
