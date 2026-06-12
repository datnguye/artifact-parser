# Design note: a `[parquet]` extra for dbt-core v2 artifacts

**Status:** draft / not scheduled — depends on an upstream schema that is not yet
published. **Author:** generated as a planning artifact. **Date:** 2026-06-12.

## Table of contents

- [Design note: a `[parquet]` extra for dbt-core v2 artifacts](#design-note-a-parquet-extra-for-dbt-core-v2-artifacts)
  - [Table of contents](#table-of-contents)
  - [Background](#background)
  - [Why this touches the framework, not just the dbt plugin](#why-this-touches-the-framework-not-just-the-dbt-plugin)
  - [Options considered](#options-considered)
  - [Recommendation](#recommendation)
  - [Sketch of the adapter approach](#sketch-of-the-adapter-approach)
  - [Open questions / blockers](#open-questions--blockers)
  - [Decision log](#decision-log)

## Background

dbt Core v2.0 (June 2026, built on the Fusion engine) introduces **Parquet
artifacts** as a high-performance alternative to the large JSON files dbt has
always emitted (`manifest.json` and friends). The pitch is that, being columnar
Parquet, they can be queried directly through DuckDB — column pruning and
predicate pushdown instead of deserializing a multi-megabyte blob. For context,
the real jaffle_shop `manifest.json` checked into `tests/data/` is ~1.2 MB for a
50-node project; production manifests reach hundreds of MB, which is exactly the
pain the columnar format is meant to remove.

Per the v2.0 announcement, the JSON artifacts **continue to be produced for
backward compatibility**, and the Parquet artifacts "encompass everything in the
JSON artifacts." So this is additive: a second ingestion mode, not a replacement.

> Reality check: as of this writing the Parquet format is announcement-level. The
> stable reference docs still describe only JSON (`--no-write-json`), and
> `schemas.getdbt.com` still tops out at the versions this repo already vendors
> (manifest v12, run-results v6, sources v3, catalog v1). The exact Parquet file
> names, the layout (one file vs. table-per-resource), and any opt-in flag are
> **not yet documented** — treat them as TBD.

## Why this touches the framework, not just the dbt plugin

`artifact_parser.core` is typed end to end around a single `dict`:

- `ArtifactParser.can_parse(artifact: dict) -> bool`
- `ArtifactParser.parse(artifact: dict) -> BaseArtifactModel`
- the dbt plugin does `model_class(**artifact)`

A columnar Parquet file is neither a `dict` nor naturally one pydantic blob. So
Parquet support is not a new codegen target — the generated pydantic models are
unaffected. It is a new **front door**: something that turns a Parquet artifact
into whatever the chosen parser contract expects.

## Options considered

1. **Adapter (smallest).** A Parquet→dict reader (`pyarrow` or `duckdb`) that
   reconstructs the JSON-equivalent dict, then reuses every existing model
   unchanged. Zero churn to `core`, the dbt plugin, or codegen. Ships as a
   `[parquet]` extra. Rides the "Parquet encompasses everything in JSON"
   guarantee. Loses the perf win (you still materialize the whole thing) but is
   correct and tiny.

2. **Native columnar plugin (medium).** Expose the Parquet artifact as a
   DuckDB-queryable relation; let callers query a 100k-node manifest without
   loading it all. This is where the real performance lives, but it strains the
   `BaseArtifactModel` return contract — a relation is not a single pydantic
   model — so it implies a second parser protocol (e.g. `parse_lazy` returning a
   query handle).

3. **Wait-and-see (cheapest).** JSON is still emitted, so do nothing until the
   Parquet schema is documented and stable.

## Recommendation

Plan for **option 1 as a `[parquet]` extra**, but **do not build until dbt
publishes the Parquet schema** — building against an announcement is how you earn
rework. The high-value, low-risk move available *now* is to make sure `core` does
not bake in "artifact == dict" any deeper than it already has, so a relational /
streaming mode (option 2) stays open later.

Concretely, until the schema lands:

- Do **not** add a `pyarrow`/`duckdb` dependency or a `[parquet]` extra yet.
- Keep the parser protocol from growing dict-only assumptions in new code.
- Track the upstream schema (see blockers) and revisit when versions appear at
  `schemas.getdbt.com` or the reference docs gain a Parquet page.

## Sketch of the adapter approach

When the schema is known, the smallest viable shape:

```
artifact_parser/dbt/parquet.py   # hand-written, gated behind [parquet] extra
    read_artifact(path) -> dict   # pyarrow/duckdb -> JSON-equivalent dict
```

Then the existing public `parse(read_artifact(path))` works unchanged, because
the dict it produces is the same shape the JSON models already validate. The
extra goes in `pyproject.toml` alongside the existing `[dbt]` / `[codegen]`
extras; tests live under `tests/artifact_parser/dbt/` mirroring the source, and a
real `.parquet` fixture joins `tests/data/`.

## Open questions / blockers

- **Schema availability** — blocker. No published Parquet schema → no codegen
  input and no fixture. Watch `schemas.getdbt.com` and the dbt artifacts docs.
- **Layout** — one Parquet file with multiple row groups, or a file per resource
  type? Determines whether the adapter reconstructs one dict or several.
- **Version signalling** — does a Parquet artifact still carry
  `metadata.dbt_schema_version` (the field the registry sniffs on)? If not, the
  plugin's `can_parse` needs a Parquet-aware path.
- **Dependency weight** — `pyarrow` is large; `duckdb` is leaner for query-style
  access. Pick per the option-1-vs-2 decision.

## Decision log

- 2026-06-12 — Chose `extra="ignore"` for generated models (codegen post-step
  `relax_extra_policy`) after real jaffle_shop manifests — a superset of the
  published v12 schema — failed to parse under `extra="forbid"`. This keeps the
  parser forward-compatible with dbt point releases and is a prerequisite mindset
  for Parquet, where the same schema-vs-reality drift will recur.
