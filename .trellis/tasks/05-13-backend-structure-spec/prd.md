# Fill skill-manager backend STRUCTURE spec

## Goal

Fill `.trellis/spec/backend/directory-structure.md` and `.trellis/spec/backend/quality-guidelines.md`, then refresh `.trellis/spec/backend/index.md` so it reflects the final file set chosen by *both* spec tasks (this one and `backend-runtime-spec`). Every section must be grounded in the actual `src/skill_manager/` and `tests/` code — no template language.

## Project At-a-Glance

- **Project**: `skill-manager` — local-first manager that subscribes to `SKILL.md` repositories, derives meta-skill drafts, and advises (does not execute) routing of natural-language tasks to skills.
- **Language**: Python 3.12+ (see `pyproject.toml`).
- **Build / runtime**: `uv` + `hatchling`. The CLI is installed as `skill-manager` / `skillmgr` via `[project.scripts]`.
- **Runtime deps**: **zero** declared in `pyproject.toml`. Only the standard library is used. Dev group has `pytest>=9.0.3`.
- **Persistence**: JSON files on disk under `~/.skill-manager` (configurable via `SKILL_MANAGER_HOME` env var or `--workspace`). There is *no* database, ORM, or HTTP API.
- **No frontend layer** — pure CLI library.

## Architecture You Need to Document

Read these files end-to-end before writing anything (they're short; the whole package is ~1500 LOC):

```
src/skill_manager/
├── __init__.py     # argparse CLI entrypoint + main(); lazy-imports subcommand modules
├── models.py       # @dataclass models: SourceRecord, Evidence, SkillRecord, RouteCandidate, MetaSkillDraft + to_jsonable()
├── workspace.py    # Workspace class (DEFAULT_WORKSPACE = ~/.skill-manager); read_json/write_json helpers
├── text.py         # Tokenization + cosine + keyword_hits utilities used by routing
├── frontmatter.py  # SKILL.md YAML-frontmatter parser (hand-rolled, no PyYAML dep)
├── sources.py      # add_source / update_sources / scan_sources; wraps `git clone|pull|rev-parse` via subprocess
├── routing.py      # route() — exact-alias rule + lexical (cosine + keyword) score with reasons + evidence
├── derive.py       # propose() clusters skills by tags/identity → MetaSkillDraft JSON + Markdown; approve() promotes to derived/
├── project.py      # project.propose() reads README/AGENTS/CLAUDE.md from a target project and writes a project skill draft
├── export.py       # apply() copies an *approved* derived draft into ~/.agents|.claude|.codex/skills/<draft_id>/SKILL.md
└── evals.py        # run() routes goldens.json queries and reports hit@1, recall@3, recall@5
```

Tests in `tests/` are flat (`test_<module>.py`) and use only `pytest` + `tmp_path`.

### Patterns to surface in the directory-structure spec

1. **One module per responsibility, flat package.** No `services/`, `controllers/`, `repositories/` — Python files live directly under `src/skill_manager/`. Each is independently importable and has its own `_workspace(workspace)` (or equivalent) entrypoint helper.
2. **CLI dispatcher in `__init__.py`**: `build_parser()` constructs `argparse` subcommands; `main()` then dispatches via `if args.command == "..."` blocks. Subcommand modules are imported *lazily inside the matching branch* (`from .routing import route` etc.), keeping startup fast and decoupling CLI wiring from feature code.
3. **Workspace is the central state holder.** `Workspace(root)` resolves seven well-known subdirs (`sources/`, `registry/`, `index/`, `derived/`, `drafts/`, `exports/`, `evals/`) and `ensure()` creates them on demand. All feature modules accept `workspace: str | Path | Workspace | None` and normalize via a private `_workspace(...)` helper that calls `ensure()`.
4. **Module-private helpers are `_snake_case`.** Public API in each module is small (often 1–4 functions). Examples: `sources._git`, `sources._workspace`, `derive._slug`, `routing._lexical_score`.
5. **`__all__` only in the package `__init__.py`** (`["build_parser", "main"]`). Other modules do not define `__all__`.
6. **Lazy subcommand imports**: the import happens inside the dispatch branch (see `__init__.py:67-110`), keeping `import skill_manager` cheap.
7. **`tests/` is flat**: one `test_<module>.py` per source module; no shared `conftest.py`. Pytest uses `tmp_path` to isolate workspace state.

### Patterns to surface in the quality-guidelines spec

1. **Mandatory `from __future__ import annotations`** at the top of every module (every existing `.py` does this). Type hints are evaluated lazily; use modern syntax (`list[str]`, `dict[str, X]`, `str | None`).
2. **Type hints are required on all public functions**; helpers may omit return type only when obvious. The codebase uses PEP 604 unions everywhere.
3. **Dataclasses for record types** (`@dataclass` in `models.py`). Convert to JSON via `to_jsonable()` which handles `Path`, `__dataclass_fields__`, lists, and dicts recursively.
4. **JSON I/O via `workspace.read_json` / `workspace.write_json`** — never `open()` + `json.load`. `write_json` ensures parent dirs and writes UTF-8 with `ensure_ascii=False, indent=2`.
5. **Subprocess discipline**: shell calls go through `sources._git(args, cwd=...)` which uses `subprocess.run` with `check=True, capture_output=True, text=True`. Never `shell=True`.
6. **String normalization** lives in `text.py` (`normalize`, `tokens`, `digest`, `cosine`, `keyword_hits`). Reuse these — do not re-roll regex/casefold loops elsewhere.
7. **Routing reasons must be explanatory strings** (`"exact alias match: citecheck"`, `"identity keyword hits: GPU算力"`). They become user-facing output; treat them as part of the public contract (`tests/test_routing.py` asserts exact reason strings).
8. **Multilingual tokens are first-class**: `text.TOKEN_RE` keeps CJK 1–3 char runs. Don't strip non-ASCII. Free-tag inference in `sources._inferred_free_tags` deliberately emits Chinese aliases.
9. **No third-party runtime deps allowed.** If a new feature needs one, justify it explicitly; pyproject's `dependencies = []` is intentional.
10. **Tests use only `pytest` + stdlib**. Pattern: create a fake workspace under `tmp_path`, write JSON registries directly, call the public function. See `tests/test_routing.py:1-30` for the helper style (`_write_registry`, `_skill`).
11. **Forbidden patterns** (verify by grep before listing — only forbid what's actually absent): `print(` outside `__init__.py:_print_json`; `logging.` (no logging library yet); `requests` / `httpx` / external HTTP; `yaml.` (frontmatter parser is hand-rolled to avoid the dep); `os.system` / `shell=True`; mutable default arguments; relative imports across modules.
12. **CLI output discipline**: every subcommand in `main()` ends with `_print_json(...)`. Output is *always* a single JSON document on stdout. Stderr is reserved for tracebacks/errors.

## Tools Available

This project has GitNexus MCP configured globally for Codex (and at project scope for Claude Code). It's a knowledge graph over this repo with **493 nodes / 840 edges / 13 communities / 25 processes** (already indexed).

> **Important**: pass `repo: "skill-manager"` on every GitNexus call — the local index also contains `or_llm_agent` so unqualified calls error with `Multiple repositories indexed`.

### GitNexus MCP (architecture-level)

| Tool | Purpose | Example |
|------|---------|---------|
| `gitnexus_query` | Find execution flows by concept | `gitnexus_query({repo: "skill-manager", query: "skill subscription"})` |
| `gitnexus_context` | 360-degree symbol view (callers/callees/processes) | `gitnexus_context({repo: "skill-manager", name: "add_source"})` |
| `gitnexus_impact` | Blast radius — what breaks if you change X | `gitnexus_impact({repo: "skill-manager", target: "Workspace", direction: "downstream"})` |
| `gitnexus_cypher` | Raw Cypher against the graph | `gitnexus_cypher({repo: "skill-manager", query: "MATCH (f:Function) WHERE f.filePath STARTS WITH 'src/skill_manager/' RETURN f.name, f.filePath LIMIT 50"})` |

Node labels in the schema include `Function`, `Class`, `File`, `Folder`, `Module`, `Community` (≈ cluster), `Process` (≈ execution flow). Common relationships are `CodeRelation` typed edges. There is **no** `Cluster` table — use `Community`.

### ABCoder MCP

Not configured for this project — Python static analysis via ABCoder is unreliable. Skip it. Use GitNexus + direct file reads instead.

### Recommended Workflow

1. **Read the source first.** The package is small (~1500 LOC). Read every file in `src/skill_manager/` before writing any spec.
2. **Use GitNexus to verify cross-module relationships** (e.g., "what calls `Workspace.ensure`?") rather than grepping.
3. **Cite real file paths and line numbers** in every spec example — `src/skill_manager/sources.py:13-39` style.
4. **Use the testsuite as ground truth** for behavior contracts. If `tests/test_routing.py` asserts a reason string, that string is part of the API.

## Files to Fill (this task)

You own these three files. Do **not** touch any other file in `.trellis/`, `src/`, or `tests/`.

### `.trellis/spec/backend/directory-structure.md`

Replace the template with:
- A real ASCII tree of `src/skill_manager/` and `tests/`.
- One-line role for each module (use the table above as a starting point but verify each entry from the code).
- "Where new code goes" rules: new subcommand → new module in `src/skill_manager/<name>.py` + lazy import inside `__init__.main()`; new dataclass → `models.py`; new tokenization helper → `text.py`; new workspace subdir → add attribute to `Workspace.__init__` and append to the `ensure()` tuple.
- Naming conventions: snake_case modules; `SKILL_MANAGER_HOME` env var; subdir names match `Workspace` attributes (`sources`, `registry`, `index`, `derived`, `drafts`, `exports`, `evals`).
- At least three "examples" with file paths, e.g. `routing.route` as the canonical "public function delegates to private `_helpers`" pattern.

### `.trellis/spec/backend/quality-guidelines.md`

Replace the template with:
- **Required patterns** section listing items 1–10 above, each with a one-line reason and a file:line reference (e.g. "Lazy subcommand imports — `src/skill_manager/__init__.py:67`").
- **Forbidden patterns** section listing item 11. **Verify each forbidden item is actually absent via Grep before listing it** — do not forbid things that the codebase already does.
- **Testing requirements**: `pytest`, `tmp_path` for filesystem isolation, no shared fixtures, one assertion-style per test, multilingual fixtures encouraged (see `tests/test_routing.py`).
- **Code review checklist** drawn from the above — concrete items, not generic platitudes.
- **CLI output discipline** (item 12).

### `.trellis/spec/backend/index.md`

Update the table to list the final file set agreed with the runtime-spec task. The final set MUST be:

| Guide | File |
|-------|------|
| Directory Structure | `./directory-structure.md` |
| Quality Guidelines | `./quality-guidelines.md` |
| State Persistence | `./state-persistence.md` |
| Error Handling | `./error-handling.md` |
| Logging Guidelines | `./logging-guidelines.md` |

Notes for the index:
- **`state-persistence.md` replaces `database-guidelines.md`** — the runtime-spec task is renaming/replacing that file because skill-manager has no database; it persists JSON on disk under a `Workspace`.
- Drop the "(To fill)" placeholders from the status column; mark each row as filled.
- Preserve the "Language: English" footer.
- Keep the header tone matching `.trellis/spec/guides/index.md`.

## Important Rules

### Stay in your lane
- ONLY modify `.trellis/spec/backend/{directory-structure,quality-guidelines,index}.md`.
- DO NOT touch `error-handling.md`, `logging-guidelines.md`, or `database-guidelines.md` — those belong to `backend-runtime-spec`.
- DO NOT modify `src/`, `tests/`, `pyproject.toml`, or any other repo file.
- DO NOT run git commands (commit, branch, etc.). Editing tracked files is fine; staging/committing is the human's job.
- You may *read* any file for analysis.

### Adapt the spec to reality
- Delete sections that don't apply to a stdlib-only Python CLI. (E.g., the template's "API endpoints" sub-bullets are irrelevant.)
- Add sections for patterns the templates miss (e.g., "Workspace-centric state" under directory-structure; "No-runtime-deps invariant" under quality-guidelines).
- Use real code blocks. Snippets like `from .routing import route` and the workspace ensure-loop should appear verbatim.

### Document reality, not ideals
- Verify every claim by reading the actual code. If something in the bullet list above contradicts what you find, trust the code.
- If a "required pattern" only exists in 1 of N modules, mark it as aspirational or drop it — don't pretend it's universal.

## Acceptance Criteria

- [ ] `directory-structure.md` contains a real ASCII tree of `src/skill_manager/` matching the on-disk layout.
- [ ] At least 3 file:line citations per guideline file (e.g., `routing.py:11-54`).
- [ ] `quality-guidelines.md` lists required patterns with concrete examples and forbidden patterns that have been verified by grep.
- [ ] `index.md` lists exactly the five files specified above, marking `database-guidelines.md` as removed / superseded.
- [ ] No "(To be filled by the team)" or `<!-- ... -->` HTML comments left in your three files.
- [ ] Substantive length: each filled file ≥ 80 lines.

## Technical Notes

- Package path: `/Users/zhangbowen/Projects/NewTools-Research/skill-manager`
- Source root: `src/skill_manager/`
- Run tests with: `uv run pytest` (Python 3.12+ via `uv`)
- GitNexus index already built; pass `repo: "skill-manager"` on every MCP call.
- The `00-bootstrap-guidelines` task in `.trellis/tasks/` is the umbrella task that triggered this work — your filled spec replaces its placeholder targets.
