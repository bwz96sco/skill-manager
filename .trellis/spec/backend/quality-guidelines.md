# Backend Quality Guidelines

> Code quality standards for `skill-manager` backend development.

---

## Purpose

Quality in this project means preserving a small, local-first, stdlib-only CLI
with predictable JSON output. The codebase favors dataclasses for records,
workspace-scoped JSON persistence, explanatory routing reasons, and flat pytest
tests that exercise public functions with temporary filesystem state.

Every guideline below is grounded in current source or tests. Patterns listed
as forbidden were verified by search before inclusion.

---

## Required Patterns

1. Start every source module with `from __future__ import annotations`.
   Reason: type hints rely on modern Python syntax such as `str | Path | None`
   and `list[str]`; current modules all use this import
   (`src/skill_manager/__init__.py:1`, `src/skill_manager/routing.py:1`,
   `src/skill_manager/workspace.py:1`).

2. Type public function signatures explicitly.
   Reason: public APIs are called directly by tests and CLI dispatch, so their
   input and output contracts must stay visible (`src/skill_manager/sources.py:14-20`,
   `src/skill_manager/routing.py:12-17`, `src/skill_manager/evals.py:10`).

3. Use PEP 604 unions and built-in generic types.
   Reason: the code targets Python 3.12+ and already uses `str | Path | Workspace | None`,
   `list[RouteCandidate]`, and `dict[str, Any]` rather than legacy `typing.List`
   or `typing.Optional` (`src/skill_manager/routing.py:12-17`,
   `src/skill_manager/project.py:57`, `src/skill_manager/export.py:46-51`).

4. Use dataclasses for persisted record shapes.
   Reason: records are simple data carriers with stable JSON fields, and the
   existing model layer is a set of dataclasses (`src/skill_manager/models.py:20-77`).

5. Convert records to JSON through `to_jsonable()`.
   Reason: it handles `Path`, dataclasses, lists, and dictionaries recursively,
   which keeps CLI and registry serialization consistent
   (`src/skill_manager/models.py:79-88`, `src/skill_manager/__init__.py:15-16`,
   `src/skill_manager/sources.py:124`).

6. Use `workspace.read_json` and `workspace.write_json` for JSON files.
   Reason: missing files get defaults, parent directories are created, UTF-8 is
   enforced, and output is indented with `ensure_ascii=False`
   (`src/skill_manager/workspace.py:42-50`, `src/skill_manager/sources.py:138-161`,
   `src/skill_manager/derive.py:233-264`).

7. Keep workspace normalization inside each feature module.
   Reason: public functions should accept `str`, `Path`, `Workspace`, or `None`
   while still ensuring the directory tree exists before state access
   (`src/skill_manager/sources.py:128-131`, `src/skill_manager/derive.py:35-41`,
   `src/skill_manager/export.py:19-25`).

8. Run git commands only through the module helper that wraps
   `subprocess.run`.
   Reason: `sources._git()` uses argument lists with `check=True`,
   `capture_output=True`, and `text=True`; this avoids shell interpolation and
   centralizes command behavior (`src/skill_manager/sources.py:201-209`).

9. Reuse `text.py` for string normalization, tokenization, digesting,
   similarity, and keyword matching.
   Reason: routing and derivation share text behavior through this module
   instead of rolling local regex/casefold loops (`src/skill_manager/text.py:10-46`,
   `src/skill_manager/routing.py:8`, `src/skill_manager/derive.py:10`).

10. Treat routing reason strings as user-facing contract.
    Reason: `RouteCandidate.reasons` is part of the returned dataclass, routing
    constructs explanatory strings, and tests assert exact strings such as
    `exact alias match: citecheck` (`src/skill_manager/models.py:58-64`,
    `src/skill_manager/routing.py:123-168`, `tests/test_routing.py:73-77`).

11. Preserve multilingual token support.
    Reason: `TOKEN_RE` intentionally captures CJK one-to-three-character runs,
    source scanning infers Chinese aliases/tags for GPU and citation workflows,
    and routing tests cover Chinese queries (`src/skill_manager/text.py:10`,
    `src/skill_manager/sources.py:236-262`, `tests/test_routing.py:96-122`).

12. Keep frontmatter parsing stdlib-only.
    Reason: `frontmatter.py` parses scalar, list, and body sections with
    `json`, `re`, and `pathlib`; source scanning depends on this parser for
    `SKILL.md` metadata (`src/skill_manager/frontmatter.py:3-9`,
    `src/skill_manager/frontmatter.py:31-68`, `src/skill_manager/sources.py:86-123`).

13. Keep runtime code stdlib-only unless a dependency is explicitly justified.
    Reason: the project declares no runtime dependencies, and production
    modules currently use standard-library imports plus local package imports
    (`pyproject.toml:9-10`, `src/skill_manager/workspace.py:3-6`,
    `src/skill_manager/text.py:3-7`, `src/skill_manager/sources.py:3-11`).

14. Keep CLI output as one JSON document on stdout.
    Reason: `_print_json()` is the only production `print()` call, and every
    dispatch branch returns through `_print_json(...)`
    (`src/skill_manager/__init__.py:15-16`, `src/skill_manager/__init__.py:74-121`).

15. Keep feature modules small and direct.
    Reason: public entrypoints delegate to module-private helpers rather than
    extra service layers; examples include `routing.route()` with scoring
    helpers and `derive.propose()` with cluster helpers
    (`src/skill_manager/routing.py:12-55`, `src/skill_manager/routing.py:142-208`,
    `src/skill_manager/derive.py:69-89`, `src/skill_manager/derive.py:212-245`).

16. Use explicit file encodings for user/project text.
    Reason: workspace JSON writes UTF-8, frontmatter reads UTF-8 with BOM
    tolerance, and project guidance reads UTF-8 (`src/skill_manager/workspace.py:45-50`,
    `src/skill_manager/frontmatter.py:32`, `src/skill_manager/project.py:71`).

17. Keep generated Markdown writes local to draft-producing modules.
    Reason: JSON state uses workspace helpers, while Markdown draft bodies are
    generated and written by `derive.py` or `project.py`
    (`src/skill_manager/derive.py:177-197`, `src/skill_manager/derive.py:234-242`,
    `src/skill_manager/project.py:33-54`, `src/skill_manager/project.py:115`).

18. Keep evals focused on routing quality metrics.
    Reason: `evals.run()` loads `evals/goldens.json`, routes each query, and
    reports rows, hit@1, recall@3, recall@5, false-positive-like count, and
    details (`src/skill_manager/evals.py:10-61`).

---

## Forbidden Patterns

The following searches were run against `src/` and `tests/` before this list
was written. Do not add these patterns unless the architecture is deliberately
changed and the relevant guideline is updated.

1. Do not use `print(` outside `src/skill_manager/__init__.py:_print_json`.
   Verified search found only `_print_json`, and CLI branches already route
   output through it (`src/skill_manager/__init__.py:15-16`,
   `src/skill_manager/__init__.py:74-121`).

2. Do not add `logging.` or import the logging library.
   Verified search found no logging usage. Current command behavior returns
   JSON payloads or raises exceptions, with no log side channel
   (`src/skill_manager/__init__.py:74-124`, `src/skill_manager/evals.py:52-61`).

3. Do not add external HTTP clients such as `requests`, `httpx`, or `aiohttp`.
   Verified search found none. Source acquisition is git-backed through
   `_git()`, while project-skill generation reads local files only
   (`src/skill_manager/sources.py:201-213`, `src/skill_manager/project.py:63-76`).

4. Do not import PyYAML or call `yaml.*`.
   Verified search found no YAML dependency usage. Frontmatter parsing is
   intentionally local and stdlib-based (`src/skill_manager/frontmatter.py:3-9`,
   `src/skill_manager/frontmatter.py:31-68`).

5. Do not use `os.system`, `shell=True`, or shell-string subprocess calls.
   Verified search found none. The production subprocess boundary passes a
   list to `subprocess.run` (`src/skill_manager/sources.py:201-209`).

6. Do not use mutable default arguments such as `=[]`, `={}`, or `=set()` in
   functions.
   Verified search found none. Models use `field(default_factory=...)` for
   mutable dataclass defaults (`src/skill_manager/models.py:51-54`,
   `src/skill_manager/models.py:64`).

7. Do not add module-level `__all__` declarations outside the package
   entrypoint.
   Verified search found only `src/skill_manager/__init__.py:127`. Feature
   modules expose their public functions by ordinary imports from the CLI or
   tests (`src/skill_manager/__init__.py:74-121`, `tests/test_sources.py:9-11`).

8. Do not introduce database, ORM, migration, or HTTP API concepts into backend
   implementation.
   The current state boundary is JSON files under `Workspace`, and source,
   routing, derivation, export, project, and eval modules use those paths
   directly (`src/skill_manager/workspace.py:13-50`,
   `src/skill_manager/sources.py:124-198`, `src/skill_manager/evals.py:64-72`).

Relative imports are not forbidden here because they are the current package
convention in source modules (`src/skill_manager/sources.py:8-11`,
`src/skill_manager/routing.py:7-9`, `src/skill_manager/derive.py:9-11`).

---

## Testing Requirements

1. Use `pytest` and stdlib-only test helpers.
   Reason: tests import pytest only where exception assertions are needed and
   otherwise use stdlib modules such as `json`, `pathlib`, and `subprocess`
   (`tests/test_sources.py:3-15`, `tests/test_derive_export.py:3-8`).

2. Use `tmp_path` for filesystem isolation.
   Reason: public functions operate on workspace directories, and tests create
   per-test workspaces instead of touching `~/.skill-manager`
   (`tests/test_sources.py:36-64`, `tests/test_derive_export.py:37-73`,
   `tests/test_evals.py:37-74`).

3. Prefer public function tests over private helper tests.
   Reason: routing, sources, derive/export, project, and eval behavior is
   asserted through public APIs such as `route`, `add_source`, `scan_sources`,
   `derive.propose`, `export.apply`, and `run`
   (`tests/test_routing.py:73-160`, `tests/test_sources.py:40-136`,
   `tests/test_derive_export.py:50-124`, `tests/test_evals.py:64-74`).

4. Keep tests flat under `tests/test_<module>.py`.
   Reason: the existing suite has no shared `conftest.py`; local helpers live
   in the test files that use them (`tests/test_routing.py:9-51`,
   `tests/test_sources.py:14-33`, `tests/test_evals.py:9-34`).

5. Assert behavior that is user-visible or persisted.
   Reason: tests assert exact route order, exact reason strings, evidence text,
   registry contents, update-log contents, exported files, and eval metrics
   (`tests/test_routing.py:73-77`, `tests/test_sources.py:42-64`,
   `tests/test_sources.py:81-86`, `tests/test_derive_export.py:61-73`,
   `tests/test_evals.py:64-74`).

6. Include multilingual fixtures when changing tokenization, inferred tags, or
   routing relevance.
   Reason: Chinese GPU queries and tags are already part of the routing and
   scanning contract (`tests/test_routing.py:96-145`,
   `tests/test_sources.py:100-136`).

7. Test CLI parser wiring separately from feature behavior.
   Reason: `test_cli_accepts_route_command` verifies parser output without
   invoking routing, while routing behavior lives in `test_routing.py`
   (`tests/test_cli.py:4-9`, `tests/test_routing.py:54-160`).

---

## Code Review Checklist

- Does every changed source module still start with `from __future__ import annotations`
  (`src/skill_manager/__init__.py:1`, `src/skill_manager/sources.py:1`)?
- Are public functions fully typed with modern unions and built-in generics
  (`src/skill_manager/routing.py:12-17`, `src/skill_manager/export.py:46-51`)?
- Did new persisted records go through dataclasses and `to_jsonable()`
  (`src/skill_manager/models.py:20-88`)?
- Does JSON file I/O use `read_json` and `write_json` rather than ad hoc
  `open()` plus `json.load`/`json.dump` (`src/skill_manager/workspace.py:42-50`)?
- Does new workspace state extend `Workspace.__init__` and `ensure()` together
  (`src/skill_manager/workspace.py:13-33`)?
- Are subprocess calls still centralized through `_git()` with argument lists
  (`src/skill_manager/sources.py:201-209`)?
- Did text matching reuse `text.normalize`, `tokens`, `cosine`, or
  `keyword_hits` where applicable (`src/skill_manager/text.py:10-46`)?
- Are routing reasons still explanatory, deterministic, and covered by tests
  (`src/skill_manager/routing.py:123-168`, `tests/test_routing.py:73-77`)?
- Are generated draft writes split correctly between JSON state and Markdown
  files (`src/skill_manager/derive.py:233-242`, `src/skill_manager/project.py:113-115`)?
- Does CLI output still flow through `_print_json()` exactly once per command
  branch (`src/skill_manager/__init__.py:74-121`)?
- Are tests isolated with `tmp_path` and focused on public behavior
  (`tests/test_sources.py:36-64`, `tests/test_derive_export.py:37-73`)?
- If matching multilingual text changed, did tests cover Chinese and mixed
  Chinese-English queries (`tests/test_routing.py:96-145`)?

---

## CLI Output Discipline

Every subcommand must emit one JSON document on stdout. The only production
printing path is `_print_json(payload)`, which converts dataclasses and paths
through `to_jsonable()` and calls `json.dumps(..., ensure_ascii=False, indent=2)`
before printing (`src/skill_manager/__init__.py:15-16`,
`src/skill_manager/models.py:79-88`).

Do not print progress text, tables, prompts, or partial JSON from feature
modules. Feature modules return Python objects or raise exceptions; `main()`
owns serialization and stdout (`src/skill_manager/__init__.py:69-124`).

The current command branches follow this rule:

| Command | Output Key or Shape | Source Reference |
|---------|---------------------|------------------|
| `source add` | serialized `SourceRecord` | `src/skill_manager/__init__.py:74-79`, `src/skill_manager/sources.py:14-40` |
| `source update` | `{"changed": [...]}` | `src/skill_manager/__init__.py:80-82`, `src/skill_manager/sources.py:43-73` |
| `scan` | `{"skills": [...]}` | `src/skill_manager/__init__.py:84-88`, `src/skill_manager/sources.py:76-125` |
| `route` | `{"candidates": [...]}` | `src/skill_manager/__init__.py:90-94`, `src/skill_manager/routing.py:12-55` |
| `derive propose` | `{"drafts": [...]}` | `src/skill_manager/__init__.py:96-101`, `src/skill_manager/derive.py:212-245` |
| `derive approve` | approval object | `src/skill_manager/__init__.py:102-104`, `src/skill_manager/derive.py:248-274` |
| `project propose` | draft summary object | `src/skill_manager/__init__.py:106-110`, `src/skill_manager/project.py:57-124` |
| `export apply` | export summary object | `src/skill_manager/__init__.py:112-116`, `src/skill_manager/export.py:46-77` |
| `eval run` | metrics object | `src/skill_manager/__init__.py:118-122`, `src/skill_manager/evals.py:10-61` |
