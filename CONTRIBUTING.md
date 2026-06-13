# Contributing to artifact-parser

Thanks for helping keep `artifact-parser` current. This guide walks you
end-to-end through the things contributors actually do: setting up the
environment, regenerating the dbt models, configuring a brand-new schema JSON,
adding a whole new artifact type, keeping tests green at 100%, and getting your
change through CI. dbt ships a new artifact schema roughly every minor release,
so most of the work here is mechanical — the framework is built so that a new
version is a regen, not a rewrite.

## Table of contents

- [Contributing to artifact-parser](#contributing-to-artifact-parser)
  - [Table of contents](#table-of-contents)
  - [TL;DR](#tldr)
  - [Prerequisites](#prerequisites)
  - [Environment setup](#environment-setup)
  - [The mental model: generated vs hand-written](#the-mental-model-generated-vs-hand-written)
  - [The codegen pipeline](#the-codegen-pipeline)
  - [Task 1: Bump an existing artifact to a new dbt version](#task-1-bump-an-existing-artifact-to-a-new-dbt-version)
  - [Task 2: Add a brand-new schema JSON by hand](#task-2-add-a-brand-new-schema-json-by-hand)
  - [Task 3: Add a whole new artifact type](#task-3-add-a-whole-new-artifact-type)
  - [Task 4: Add a whole new plugin (non-dbt tool)](#task-4-add-a-whole-new-plugin-non-dbt-tool)
  - [The `extra="ignore"` invariant — do not undo it](#the-extraignore-invariant--do-not-undo-it)
  - [Testing](#testing)
  - [Code quality](#code-quality)
  - [CI gates you must pass](#ci-gates-you-must-pass)
  - [Releasing](#releasing)
  - [Pull request checklist](#pull-request-checklist)

## TL;DR

```bash
task install                       # sync the uv env (incl. dev group)
task git-hooks                     # install pre-commit + commit-msg hooks
task codegen:fresh -- --discover   # pull latest dbt schemas, refresh versions, regen everything
task format                        # ruff format + autofix
task test                          # pytest at 100% coverage
```

If `git diff` shows nothing under `src/artifact_parser/dbt/generated/` after a
clean regen and the tests pass, you're in sync with what CI expects.

## Prerequisites

- **Python 3.10–3.13** (the lib targets `>=3.10`; CI runs the full matrix).
- **[uv](https://docs.astral.sh/uv/)** — the package/environment manager.
- **[Task](https://taskfile.dev/)** (`task`) — the command runner. Every workflow
  below has a `task` shortcut; the raw commands are shown too if you'd rather not
  install it.
- Network access for codegen runs that download schemas (the `--skip-download`
  variants work offline against the committed schemas).

## Environment setup

```bash
git clone https://github.com/datnguye/artifact-parser
cd artifact-parser
task install        # uv sync --group dev  → installs artifact-parser[codegen,dbt] + dev tooling
task git-hooks      # installs ruff pre-commit + commit-msg hooks
```

The `dev` dependency group pulls in everything you need: the `codegen` extra
(`typer`, `jinja2`, `datamodel-code-generator`), the `dbt` extra, plus `pytest`,
`pytest-cov`, `ruff`, and `pre-commit`. There is no separate "maintainer install"
to remember — `task install` is the one true setup.

Run `task --list` any time to see the full menu.

## The mental model: generated vs hand-written

This boundary is the single most important thing to internalize, and it is now
**physical** — everything generated lives under one directory:

```
src/artifact_parser/dbt/generated/    ← GENERATED. Never hand-edit. Clobbered on regen.
├── __init__.py
├── version_map.py                    ←   schema-URL → model class table
├── parser.py                         ←   parse_<artifact>[_vN] public API
└── models/<package>/<package>_vN.py  ←   one pydantic model per artifact+version
```

Everything else is hand-written and yours to edit:

| Hand-written                                   | What it is                                      |
|------------------------------------------------|-------------------------------------------------|
| `src/artifact_parser/core/**`                  | source-agnostic framework (base, parser, registry, exceptions) |
| `src/artifact_parser/dbt/plugin.py`            | the `DbtArtifactParser` plugin                  |
| `src/artifact_parser/dbt/utils.py`             | schema-version sniffing                         |
| `src/artifact_parser/dbt/__init__.py`          | plugin registration                             |
| `src/artifact_parser/dbt/resources/**/*.json`  | committed dbt schemas — the codegen **input**   |
| `src/codegen/**`                               | the developer codegen CLI (typer)               |
| `src/codegen/dbt/artifact_spec.py`             | the artifact-family catalogue (you'll edit this) |
| `src/codegen/dbt/templates/*.jinja`            | jinja templates for `version_map.py` / `parser.py` |

The whole `generated/` tree is safe to delete and rebuild:

```bash
rm -rf src/artifact_parser/dbt/generated
task codegen:regen      # rebuild from cached schemas (offline)
```

While `generated/` is absent, `import artifact_parser` still works — the dbt
plugin just doesn't register (you get a warning). That's deliberate: the codegen
CLI that rebuilds it must be importable even when there's nothing to register
yet. (A parser that can't bootstrap itself would be a sad little ouroboros.)

**Golden rule:** to change generated output, edit the **template** or the
**spec**, then regenerate. Never patch a file under `generated/` — the next
`codegen` run erases your edit, and the CI sync gate will fail the PR anyway.

## The codegen pipeline

What `codegen dbt` actually does, per selected `(artifact, version)`:

1. **Download** the schema from
   `https://schemas.getdbt.com/dbt/<name>/<version>.json`
   into `src/artifact_parser/dbt/resources/<name>/<name>_<version>.json`
   (skipped with `--skip-download`).
2. **Generate** a pydantic v2 model with `datamodel-codegen` into
   `src/artifact_parser/dbt/generated/models/<package>/<package>_<version>.py`,
   then post-process it through `relax_extra_policy` (see
   [the invariant below](#the-extraignore-invariant--do-not-undo-it)).
3. **Rewrite** the three generated index files from jinja templates:
   `generated/__init__.py`, `generated/version_map.py`, `generated/parser.py` —
   so the schema-URL → model-class table and the `parse_*` API always match
   what's on disk.

The CLI surface (`uv run python -m codegen dbt ...`, or the `codegen` console
script):

```bash
codegen dbt                       # all artifacts, all versions, fresh download
codegen dbt manifest              # all manifest versions, fresh download
codegen dbt manifest v12          # just manifest v12
codegen dbt run-results v5 v6     # two specific versions
codegen dbt --skip-download       # regen everything from cached resources/ (offline)
codegen dbt --discover            # probe getdbt.com for ALL published versions, refresh the
                                  #   versions table, then download + generate them all
```

`--discover` and `--skip-download` are mutually exclusive (one needs the network,
the other forbids it). The version list lives in `src/codegen/dbt/versions.py`
and is (re)written by `--discover`; discovery probes `v1.json`, `v2.json`, …
until it sees a run of 404s.

The `task` wrappers — each also runs `task format` afterward:

| Goal                                         | Task                              |
|----------------------------------------------|-----------------------------------|
| Regen from cached schemas (offline)          | `task codegen:regen`              |
| Regen a single target                        | `task codegen -- manifest v12`    |
| Download latest + regen                      | `task codegen:fresh`              |
| Discover every published version + regen all | `task codegen:fresh -- --discover`|
| Regen only if a schema checksum moved (gate) | `task codegen:check`             |

## Task 1: Bump an existing artifact to a new dbt version

The common case: dbt 1.x ships `manifest v13` and we want to support it.

```bash
# 1. Pull it down and generate, in one shot. --discover finds every new published
#    version across all artifacts and refreshes src/codegen/dbt/versions.py:
task codegen:fresh -- --discover

#    …or, if you know exactly what's new and want to scope it:
task codegen:fresh -- manifest v13
```

This produces, with zero hand-editing of generated code:

- `src/artifact_parser/dbt/resources/manifest/manifest_v13.json` — the schema.
- `src/artifact_parser/dbt/generated/models/manifest/manifest_v13.py` — class
  `ManifestV13`.
- updated `generated/version_map.py` (adds the `v13` URL → `ManifestV13` entry).
- updated `generated/parser.py` (adds `parse_manifest_v13`).

The hand-written `plugin.py` and `utils.py` **do not change** — they dispatch
through the generated version map, so a new version wires itself in.

Then add test coverage (see [Testing](#testing)) and verify:

```bash
task format
task test
```

## Task 2: Add a brand-new schema JSON by hand

Sometimes you have a schema that isn't (yet) on `schemas.getdbt.com`, or you want
to pin a hand-tweaked copy. The resources directory is the source of truth, so
you can just drop the file in and regenerate offline:

```bash
# 1. Place the schema where codegen expects it — the path encodes name + version:
#    src/artifact_parser/dbt/resources/<name>/<name>_<version>.json
cp my-manifest-v13.json \
  src/artifact_parser/dbt/resources/manifest/manifest_v13.json

# 2. Make sure the version is registered in src/codegen/dbt/versions.py
#    (VERSIONS["manifest"] must include "v13"). --discover writes this for you,
#    or add it by hand if the version isn't published upstream.

# 3. Regenerate from cache — no network:
task codegen:regen
```

The filename pattern is load-bearing: codegen derives the target model path from
`<name>_<version>.json`. Get it wrong and codegen won't find your schema.

## Task 3: Add a whole new artifact type

dbt grows a fifth artifact family one day. The catalogue lives in
`src/codegen/dbt/artifact_spec.py`:

```python
ARTIFACT_SPECS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(name="catalog", package="catalog", class_prefix="Catalog"),
    ArtifactSpec(name="manifest", package="manifest", class_prefix="Manifest"),
    ArtifactSpec(name="run-results", package="run_results", class_prefix="RunResults"),
    ArtifactSpec(name="sources", package="sources", class_prefix="Sources"),
)
```

Each field has a precise job:

- **`name`** — the dbt artifact name exactly as it appears in schema URLs and
  filenames (hyphenated, e.g. `"run-results"`).
- **`package`** — the Python-safe module/directory stem (e.g. `"run_results"` —
  hyphens become underscores).
- **`class_prefix`** — the generated model class prefix (e.g. `"RunResults"`, so
  v6 becomes `RunResultsV6`).

To add one (call it `freshness`):

```python
ArtifactSpec(name="freshness", package="freshness", class_prefix="Freshness"),
```

Then discover its versions and generate:

```bash
task codegen:fresh -- --discover     # probes getdbt.com, finds freshness v1, v2…
```

`--discover` reads versions into `src/codegen/dbt/versions.py` (keyed by `name`),
and `ArtifactSpec.versions` resolves them dynamically from that table. Add a
fixture and (ideally) a round-trip test, then `task test`.

## Task 4: Add a whole new plugin (non-dbt tool)

The framework is source-agnostic — dbt is just the first plugin. To support a
different tool's artifacts, mirror `src/artifact_parser/dbt/`:

1. Create `src/artifact_parser/<tool>/` with a `plugin.py` implementing the
   `ArtifactParser` protocol from `core/parser.py` (`name`, `can_parse`,
   `parse`).
2. Register the instance with the shared `registry` in the package
   `__init__.py`, the same way `dbt/__init__.py` does.
3. If the models are schema-generated, add a sibling `src/codegen/<tool>/`
   mirroring `codegen/dbt/` (spec, generator, templates), and a `codegen <tool>`
   subcommand.
4. Add a `<tool>` extra in `pyproject.toml` and wire it into the `dev` group.
5. Mirror the test layout under `tests/artifact_parser/<tool>/`.

If you're contemplating this, open an issue first so we can agree on the shape —
it's a bigger surface than a version bump.

## The `extra="ignore"` invariant — do not undo it

dbt's published schemas set `additionalProperties: false`, so `datamodel-codegen`
emits `extra="forbid"` on every model. But **real artifacts are a superset of the
published schema** — a real dbt 1.11 `manifest.json` carries macro `config` fields
the v12 schema never mentions. A strict model rejects those outright (hundreds of
validation errors), which is useless in practice.

So `generator.generate_model` runs a post-step, `relax_extra_policy`, that
rewrites `extra='forbid'` → `extra='ignore'` in the raw codegen output (single
quotes — it runs *before* `task format` normalises them).

**Do not undo this.** The round-trip tests in
`tests/artifact_parser/dbt/test_roundtrip.py` parse real artifacts from
`tests/data/` and will fail loudly the moment a generated model goes back to
`forbid`. If you ever hand-edit a generated model (you shouldn't), this is the
trap that catches it.

## Testing

`tests/` mirrors `src/` directory-for-directory:

```
tests/
├── conftest.py                              # shared fixtures (DRY — no per-test literals)
├── data/                                    # real dbt artifacts for round-trip tests
├── artifact_parser/core/                    # framework tests
├── artifact_parser/dbt/                     # parser, utils, round-trip tests
└── codegen/dbt/                             # generator + CLI tests
```

Run the suite with the coverage gate (this is exactly what CI runs):

```bash
task test
# → uv run pytest --cov=artifact_parser --cov=codegen \
#     --cov-report=term-missing --cov-fail-under=100
```

**Coverage must stay at 100%.** Generated model code is omitted from coverage
(it's `datamodel-codegen`'s output, trusted wholesale); the dispatch logic is
covered through a representative sample of the public `parse_*` API rather than
every single version.

When you add a version, add two things:

1. **A minimal fixture** in `tests/conftest.py` — a dict with the right
   `metadata.dbt_schema_version` URL and the schema's required (empty)
   collections. This exercises dispatch without a giant artifact literal. Follow
   the existing fixtures rather than inventing a new shape (DRY).
2. **(Recommended) a round-trip case** in
   `tests/artifact_parser/dbt/test_roundtrip.py`. Export a real artifact from a
   dbt project, drop it in `tests/data/<name>_<version>.json`, and assert the
   parsed model has the structure you expect. This is what guards the
   `extra="ignore"` invariant for the new version.

## Code quality

The project follows strict, automated conventions:

```bash
task format     # uv run ruff format . && uv run ruff check --fix .
task lint       # uv run ruff format --check . && uv run ruff check .   (no writes)
```

House rules (most are ruff-enforced, so the linter will tell you):

- **No relative imports**, and **all imports at module top** (`ruff PLC0415`).
- **One class per file** (exception: multiple exception classes may share a file).
- **No nested functions or classes** — define everything at module level.
- **Specific exception types** from `core/exceptions.py` — never a bare `except:`.
- **No backward-compat shims** unless explicitly requested.
- **DRY in tests** — share fixtures through `tests/conftest.py`.

The pre-commit hooks (installed by `task git-hooks`) run trailing-whitespace /
end-of-file fixers and `ruff` + `ruff-format` on every commit, so most of this is
caught before you even push.

## CI gates you must pass

`.github/workflows/ci.yml` runs on every push and PR:

1. **`test`** — across Python 3.10, 3.11, 3.12, 3.13: `task lint` (format-check +
   ruff) then `task test` (pytest at 100% coverage).
2. **`codegen-in-sync`** — regenerates from the committed schemas
   (`codegen dbt --skip-download`), runs `ruff format`, then:

   ```bash
   git diff --exit-code -- src/artifact_parser/dbt/generated
   ```

   If a regen would change anything under `generated/`, the gate fails. This is
   what catches a hand-edited generated file, or a spec/template change that
   wasn't followed by a regen.

The single best way to never be surprised by CI:

```bash
task codegen:regen   # rebuild generated/ from cached schemas
task lint
task test
git status           # nothing unexpected under generated/?  good.
```

## Releasing

Releases are maintainer-driven and you don't need to touch versions —
`hatch-vcs` derives the version from the git tag. `.github/workflows/release.yml`:

- **`build`** — lints, tests at 100% coverage, builds the sdist + wheel, and runs
  `twine check`.
- **Publish to PyPI** via Trusted Publishing when a GitHub Release is published.
- **Publish to TestPyPI** via manual workflow dispatch, for dry runs.

If you're a contributor (not a maintainer), you can ignore this section — just get
your PR green.

## Pull request checklist

- [ ] `task lint` passes (ruff format-check + check, no writes needed).
- [ ] `task test` passes at **100% coverage**.
- [ ] If you touched schemas, the spec, or templates: you ran a regen and
      committed the resulting `generated/` changes (`task codegen:regen` then
      check `git status`).
- [ ] You did **not** hand-edit anything under
      `src/artifact_parser/dbt/generated/`.
- [ ] New versions have a fixture in `conftest.py` (and ideally a round-trip case
      with real data in `tests/data/`).
- [ ] Generated models still use `extra="ignore"` (the round-trip tests confirm
      this).

Welcome aboard — and thanks for keeping the parser one step ahead of dbt's
release train.
