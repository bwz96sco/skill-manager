# Backend Directory Structure

> How backend code is organized in `skill-manager`.

---

## Purpose

`skill-manager` is a stdlib-only Python CLI package. Backend code is a flat
package under `src/skill_manager/`, and tests are a flat pytest suite under
`tests/`. The CLI parses commands in `src/skill_manager/__init__.py:19-66` and
dispatches into feature modules in `src/skill_manager/__init__.py:69-124`.

GitNexus verification confirmed the indexed source file set is exactly the
eleven Python files shown below, and direct source reads confirmed the same
roles and call boundaries.

---

## Directory Layout

```text
src/
`-- skill_manager/
    |-- __init__.py
    |-- derive.py
    |-- evals.py
    |-- export.py
    |-- frontmatter.py
    |-- models.py
    |-- project.py
    |-- routing.py
    |-- sources.py
    |-- text.py
    `-- workspace.py

tests/
|-- test_cli.py
|-- test_derive_export.py
|-- test_evals.py
|-- test_frontmatter.py
|-- test_routing.py
`-- test_sources.py
```

Ignore generated `__pycache__/` directories. They are not source layout and
must not be documented as project structure.

---

## Module Roles

| Module | Role | Source Reference |
|--------|------|------------------|
| `src/skill_manager/__init__.py` | Package entrypoint, argparse command tree, lazy command dispatcher, JSON stdout helper. | `src/skill_manager/__init__.py:15-16`, `src/skill_manager/__init__.py:19-66`, `src/skill_manager/__init__.py:69-124` |
| `src/skill_manager/models.py` | Dataclass record types for sources, evidence, skills, route candidates, meta-skill drafts, plus JSON conversion. | `src/skill_manager/models.py:20-77`, `src/skill_manager/models.py:79-88` |
| `src/skill_manager/workspace.py` | Workspace root, seven state directories, path normalization, JSON read/write helpers. | `src/skill_manager/workspace.py:9-39`, `src/skill_manager/workspace.py:42-50` |
| `src/skill_manager/text.py` | Shared normalization, tokenization, digest, cosine similarity, and keyword hit utilities. | `src/skill_manager/text.py:10-46` |
| `src/skill_manager/frontmatter.py` | Hand-rolled `SKILL.md` YAML-like frontmatter parser using stdlib JSON and regex helpers. | `src/skill_manager/frontmatter.py:9-28`, `src/skill_manager/frontmatter.py:31-68` |
| `src/skill_manager/sources.py` | Source subscription, git update, `SKILL.md` scanning, tag and alias inference, update-log maintenance. | `src/skill_manager/sources.py:14-40`, `src/skill_manager/sources.py:43-73`, `src/skill_manager/sources.py:76-125` |
| `src/skill_manager/routing.py` | Advisory routing: load registry, exact-match rule, lexical scoring, user-facing reasons, evidence return. | `src/skill_manager/routing.py:12-55`, `src/skill_manager/routing.py:123-168` |
| `src/skill_manager/derive.py` | Registry clustering, meta-skill draft JSON/Markdown proposal, approval into `derived/`. | `src/skill_manager/derive.py:69-89`, `src/skill_manager/derive.py:147-197`, `src/skill_manager/derive.py:212-274` |
| `src/skill_manager/project.py` | Project skill draft generation from `README.md`, `AGENTS.md`, and `CLAUDE.md`. | `src/skill_manager/project.py:11-20`, `src/skill_manager/project.py:57-124` |
| `src/skill_manager/export.py` | Export approved generated drafts into target skill directories. | `src/skill_manager/export.py:10-16`, `src/skill_manager/export.py:46-77` |
| `src/skill_manager/evals.py` | Routing golden eval runner with hit@1, recall@3, recall@5, and false-positive-like reporting. | `src/skill_manager/evals.py:10-61`, `src/skill_manager/evals.py:64-78` |

---

## Organization Rules

1. Keep backend code flat under `src/skill_manager/`; do not introduce
   `services/`, `controllers/`, or `repositories/` layers without a concrete
   reason. Current feature modules are direct siblings and import shared
   helpers from `models`, `text`, and `workspace` as needed
   (`src/skill_manager/sources.py:8-11`, `src/skill_manager/routing.py:7-9`).

2. Put new CLI commands in a new `src/skill_manager/<name>.py` module when the
   behavior is a separate feature area, then wire only argparse and lazy
   dispatch in `__init__.py`. The existing command tree is built centrally in
   `src/skill_manager/__init__.py:19-66`, while command implementations are
   imported inside the matching branch at `src/skill_manager/__init__.py:74-121`.

3. Keep `src/skill_manager/__init__.py` limited to CLI wiring, `_print_json`,
   and exported entrypoints. It currently exposes only `build_parser` and
   `main` through `__all__` (`src/skill_manager/__init__.py:127`).

4. Add new persistent record types to `models.py`. Existing state shapes are
   dataclasses, and `to_jsonable()` is the central conversion path for
   dataclasses, paths, lists, and dictionaries (`src/skill_manager/models.py:20-88`).

5. Add new workspace directories only by extending `Workspace.__init__` and
   the `ensure()` directory tuple together. The current attributes are
   `sources`, `registry`, `index`, `derived`, `drafts`, `exports`, and `evals`
   (`src/skill_manager/workspace.py:13-33`).

6. Keep feature APIs workspace-aware. Public functions should accept
   `str | Path | Workspace | None` when they operate on workspace state, then
   normalize through `Workspace` or a module-private `_workspace` helper
   (`src/skill_manager/sources.py:14-20`, `src/skill_manager/sources.py:128-131`,
   `src/skill_manager/derive.py:35-41`, `src/skill_manager/export.py:19-25`).

7. Add tokenization, scoring, normalization, or hashing helpers to `text.py`
   instead of reimplementing those loops inside feature modules. Routing
   imports `cosine`, `keyword_hits`, `normalize`, and `tokens` directly from
   `text.py` (`src/skill_manager/routing.py:8`, `src/skill_manager/text.py:10-46`).

8. Keep `frontmatter.py` responsible for `SKILL.md` metadata parsing. Source
   scanning delegates metadata and body parsing there before building
   `SkillRecord` values (`src/skill_manager/sources.py:86-123`,
   `src/skill_manager/frontmatter.py:31-68`).

9. Keep tests flat and module-oriented. The suite has one `test_<module>.py`
   file per main feature area, and tests call public functions with temporary
   workspaces instead of sharing global fixtures (`tests/test_sources.py:36-64`,
   `tests/test_routing.py:54-160`).

10. Do not create a frontend, HTTP API, database layer, or ORM directory for
    this package. Persistence is filesystem JSON through `Workspace` and
    `read_json`/`write_json` (`src/skill_manager/workspace.py:42-50`), and
    the CLI script entrypoints target `skill_manager:main` (`pyproject.toml:12-14`).

---

## Where New Code Goes

| Change | Location | Required Follow-up |
|--------|----------|--------------------|
| New subcommand | `src/skill_manager/<command>.py` | Add parser setup in `build_parser()` and lazy import/dispatch in `main()` like `route` (`src/skill_manager/__init__.py:39-43`, `src/skill_manager/__init__.py:90-94`). |
| New persistent record | `src/skill_manager/models.py` | Use `@dataclass` and ensure `to_jsonable()` can serialize it (`src/skill_manager/models.py:20-88`). |
| New workspace directory | `src/skill_manager/workspace.py` | Add an attribute and add the same path to `ensure()` (`src/skill_manager/workspace.py:13-33`). |
| New registry JSON file | Feature module plus `workspace.write_json` | Keep parent directory creation and formatting centralized (`src/skill_manager/workspace.py:48-50`). |
| New routing signal | `src/skill_manager/text.py` or `src/skill_manager/routing.py` | Put reusable text logic in `text.py`; keep candidate construction in `routing.route` (`src/skill_manager/text.py:10-46`, `src/skill_manager/routing.py:12-55`). |
| New source-scan inference | `src/skill_manager/sources.py` | Extend `_inferred_free_tags`, `_inferred_aliases`, or `_tags` rather than changing routing for source metadata (`src/skill_manager/sources.py:236-280`). |
| New draft-generation behavior | `src/skill_manager/derive.py` or `src/skill_manager/project.py` | `derive.py` is for registry clusters; `project.py` is for local project guidance files (`src/skill_manager/derive.py:212-245`, `src/skill_manager/project.py:57-124`). |
| New export target | `src/skill_manager/export.py` plus CLI choices | Add default destination or explicit target handling in `_destination`, then add the argparse choice (`src/skill_manager/export.py:10-35`, `src/skill_manager/__init__.py:55-60`). |
| New eval metric | `src/skill_manager/evals.py` | Compute inside `run()` and include it in the returned JSON object (`src/skill_manager/evals.py:10-61`). |

---

## Naming Conventions

1. Source modules use lower-case `snake_case` filenames, and public functions
   use lower-case function names such as `add_source`, `scan_sources`,
   `route`, `propose`, `approve`, `apply`, and `run`
   (`src/skill_manager/sources.py:14-76`, `src/skill_manager/routing.py:12-17`,
   `src/skill_manager/export.py:46-51`).

2. Module-private helpers use leading-underscore `snake_case`. Examples include
   `_workspace`, `_git`, `_slug`, `_lexical_score`, and `_destination`
   (`src/skill_manager/sources.py:128-131`, `src/skill_manager/sources.py:201-209`,
   `src/skill_manager/derive.py:44-47`, `src/skill_manager/routing.py:142-168`,
   `src/skill_manager/export.py:28-35`).

3. Workspace directory attribute names match on-disk directory names exactly:
   `sources`, `registry`, `index`, `derived`, `drafts`, `exports`, and `evals`
   (`src/skill_manager/workspace.py:15-21`).

4. The default workspace comes from `SKILL_MANAGER_HOME` and falls back to
   `~/.skill-manager`; keep that environment variable name stable
   (`src/skill_manager/workspace.py:9`).

5. CLI subcommand names are short verbs or nouns matching module names where
   possible: `source`, `scan`, `route`, `derive`, `project`, `export`, and
   `eval` (`src/skill_manager/__init__.py:27-64`).

6. Output object keys are stable JSON names, not display strings. Existing
   commands return keys like `changed`, `skills`, `candidates`, `drafts`, and
   `status` (`src/skill_manager/__init__.py:78-121`,
   `src/skill_manager/export.py:72-77`).

---

## Examples To Follow

### Public Function Delegates To Private Helpers

`routing.route()` is the canonical pattern. It loads state, computes query
forms, delegates exact and lexical logic to private helpers, sorts candidates,
and returns dataclass records (`src/skill_manager/routing.py:12-55`). The
helper boundary keeps scoring details local to the module
(`src/skill_manager/routing.py:123-208`).

```python
from .routing import route
```

The CLI imports that public function only inside the `route` command branch
(`src/skill_manager/__init__.py:90-94`).

### Workspace-Centric Feature Module

`sources.add_source()` accepts a workspace argument, normalizes it through
`_workspace()`, reads/writes registries through workspace helpers, and leaves
source checkout paths under `workspace.sources` (`src/skill_manager/sources.py:14-40`,
`src/skill_manager/sources.py:128-161`).

```python
ws = _workspace(workspace)
records = _load_sources(ws)
destination = _source_dir(ws, name)
```

### Shared State Directories

`Workspace.ensure()` is the authoritative list of directories that may be
created for normal operation (`src/skill_manager/workspace.py:23-33`). Additions
must update both the attribute list and the ensure tuple.

```python
for path in (
    self.sources,
    self.registry,
    self.index,
    self.derived,
    self.drafts,
    self.exports,
    self.evals,
):
    path.mkdir(parents=True, exist_ok=True)
```

### Generated Draft Lifecycle

`derive.propose()` reads `registry/skills.json`, writes draft JSON and Markdown
under `drafts/`, and `derive.approve()` promotes approved files into
`derived/` (`src/skill_manager/derive.py:212-245`,
`src/skill_manager/derive.py:248-274`). `export.apply()` then copies only
approved generated drafts into a target skill directory
(`src/skill_manager/export.py:46-77`).

### Project Skill Lifecycle

`project.propose()` is separate from `derive.propose()` because it reads local
project guidance files instead of skill registry clusters. It reads
`README.md`, `AGENTS.md`, and `CLAUDE.md`, then writes draft JSON and Markdown
with provenance (`src/skill_manager/project.py:11-20`,
`src/skill_manager/project.py:57-124`).
