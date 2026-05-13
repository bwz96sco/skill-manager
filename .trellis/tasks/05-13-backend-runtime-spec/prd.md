# Fill skill-manager backend RUNTIME spec

## Goal

Fill the three "runtime" specs for skill-manager:

1. Replace `.trellis/spec/backend/database-guidelines.md` with a new file `.trellis/spec/backend/state-persistence.md` (skill-manager has no DB; it persists JSON on disk under a `Workspace`).
2. Fill `.trellis/spec/backend/error-handling.md`.
3. Fill `.trellis/spec/backend/logging-guidelines.md` (skill-manager has no logging library — document the "structured stdout, exceptions to stderr" convention).

Every section must cite real file paths from `src/skill_manager/` and ideally `tests/`. No template prose.

## Project At-a-Glance

- **Project**: `skill-manager` — local-first manager that subscribes to `SKILL.md` repositories, derives meta-skill drafts, and advises routing of natural-language tasks to skills.
- **Language**: Python 3.12+ (see `pyproject.toml`); zero runtime dependencies (stdlib only).
- **Persistence**: JSON files under `~/.skill-manager/<subdir>/...`. No database. No HTTP API.
- **Logging**: there is no `logging` library import. CLI output is a single JSON document on stdout via `print(json.dumps(..., ensure_ascii=False, indent=2))` (see `src/skill_manager/__init__.py:_print_json`).
- **Error path**: Python exceptions surface to the CLI; `argparse` and the unhandled-exception path produce stderr tracebacks. Helpers raise `ValueError`, `KeyError`, `FileNotFoundError` from the standard hierarchy.

## Architecture You Need to Document

Read every file in `src/skill_manager/` (≈1500 LOC total) before writing. The persistence + error + IO surface is concentrated in:

```
src/skill_manager/
├── workspace.py    # Workspace class + read_json / write_json; DEFAULT_WORKSPACE = ~/.skill-manager
├── models.py       # @dataclass records + to_jsonable() (used by _print_json)
├── sources.py      # subprocess git invocation; raises CalledProcessError, ValueError, KeyError; writes sources.json + update-log.json
├── routing.py      # reads registry/skills.json; never writes
├── derive.py       # writes drafts/*.json + drafts/*.md; reads registry/skills.json
├── project.py      # raises FileNotFoundError if project dir missing/no guidance files; writes drafts/project-*.json|md
├── export.py       # writes ~/.<host>/skills/<draft_id>/SKILL.md; raises ValueError for unknown target/unapproved drafts
├── evals.py        # reads evals/goldens.json; pure-function metrics
└── __init__.py     # argparse + _print_json(payload) sole sink
```

### State persistence patterns to surface

1. **`Workspace` is the on-disk schema.** `workspace.py:Workspace.__init__` declares seven well-known subdirs:
   - `sources/<name>/` — git clones of subscribed skill repos (read-only working trees)
   - `registry/sources.json` — list of `SourceRecord` (name, url, skill_root, ref, commit)
   - `registry/skills.json` — list of `SkillRecord` after `scan`
   - `registry/update-log.json` — append-only log of source-update events (`{source, before, after, changed_skill_ids, affected_drafts}`)
   - `drafts/<draft_id>.json` + `drafts/<draft_id>.md` — unapproved meta/project skills
   - `derived/<draft_id>.json` + `derived/<draft_id>.md` — approved drafts ready for export
   - `exports/` — currently unused but reserved
   - `evals/goldens.json` — routing golden queries
   - `index/` — reserved for future use
2. **JSON I/O always goes through `workspace.read_json(path, default)` and `workspace.write_json(path, payload)`.** Both UTF-8, `ensure_ascii=False`, `indent=2`. `write_json` creates parent dirs.
3. **Workspace resolution is uniform**: every feature module accepts `workspace: str | Path | Workspace | None` and normalizes via a `_workspace(workspace)` helper that calls `ensure()`. Example: `sources.py:118-121`, `derive.py:23-29`, `routing.py:14-15` (note: routing.py does *not* call `ensure()` — it only reads).
4. **Tolerant readers**: `_load_sources` and `_load_skills` accept either a raw list or `{"skills": [...]}` / `{"sources": [...]}` envelope (`sources.py:_load_sources`, `routing.py:_load_skills`). Surface this as the official "store-and-evolve" rule.
5. **Append-only update log**: `sources._append_update_log` (sources.py near the bottom) reads, mutates in-place, rewrites the whole JSON file. Document this pattern for any other append-only file.
6. **External git checkouts are mutated by subprocess only**, never edited in-place by skill-manager. `sources.add_source` calls `_git(["clone", ...])`; `sources.update_sources` calls `_git(["pull", "--ff-only"])`. We trust git to manage that subtree.
7. **Default workspace is `~/.skill-manager`**, overridable via `SKILL_MANAGER_HOME` env var (`workspace.py:DEFAULT_WORKSPACE`) or CLI `--workspace`. The CLI's `--workspace` flag wins (see `__init__.py:_workspace_arg`).
8. **Content-addressed digests**: `text.digest(text)` is `sha256` hex; used for skill registry digests, draft seeds, chunk hashes (`sources.py:scan_sources`, `derive.py:_draft_from_cluster`, `project.py:propose`).
9. **Provenance is mandatory** for every derived artifact: every `Evidence` carries `source`, `skill_id`, `path`, `commit`, `line_start`, `line_end`, `chunk_hash`, `text`. Drafts include a "Provenance" markdown section (`derive._markdown`).

### Error-handling patterns to surface

1. **Built-in exceptions, not custom hierarchy.** The whole package raises only `ValueError`, `KeyError`, `FileNotFoundError`, and lets `subprocess.CalledProcessError` propagate. No custom exception classes exist.
2. **Conflict detection**: `sources.add_source` raises `ValueError("source already exists with different configuration: {name}")` when an existing source's URL/path/ref changed (sources.py:24-27). The message embeds the offending name.
3. **Missing source**: `sources.update_sources` raises `KeyError(selected)` for unknown source names (sources.py:51-52).
4. **Missing input**: `project.propose` raises `FileNotFoundError` if the target dir is missing OR if none of `README.md`/`AGENTS.md`/`CLAUDE.md` exist (`project.py:53-67`).
5. **Approval / target validation**: `export.apply` raises `ValueError("Draft … is not approved")`, `ValueError("Unknown export target …")`, `ValueError("Draft … is not a generated meta/project skill")`, `FileNotFoundError("Approved generated draft … is missing …")` (export.py:55-72).
6. **Argparse-driven CLI errors**: invalid subcommand or missing required argument → `parser.error(...)` (auto-exit 2 with stderr message). See `__init__.py:main` final `parser.error("Unhandled command")`.
7. **Subprocess fallback pattern**: `sources.add_source` first tries `git clone --branch <ref>`; on `CalledProcessError` it falls back to a plain clone + `git checkout <ref>` (`sources.py:30-34`). This pattern is explicit "try the better call, downgrade on failure".
8. **No `try/except` blocks for control flow.** The codebase uses exceptions to *fail loudly*, not as flow. Helper exceptions are raised at the boundary; callers normally do not catch them.
9. **Test-asserted contracts**: `tests/test_sources.py` and `tests/test_derive_export.py` (read them) pin exact exception types — treat those as the contract.

### Logging / output patterns to surface

1. **No `logging` module imports anywhere in `src/`.** Verify via grep before writing this.
2. **Every CLI subcommand returns a JSON payload** via `_print_json(payload)` (`__init__.py:11-13`). `to_jsonable()` (models.py) walks dataclasses + `Path` to dicts/strings.
3. **One JSON document per command invocation** — no streaming, no progress lines, no multi-document output. This makes the CLI script-friendly (`uv run skillmgr scan | jq …`).
4. **Errors go to stderr via Python's default uncaught-exception printer** (argparse via `parser.error`, otherwise traceback). The CLI exit code is non-zero on raise.
5. **No PII concerns** (it's a local dev tool) but git URLs and project paths *do* land in stdout JSON. Document that exports may contain absolute filesystem paths.
6. **Debug-style printing forbidden** in modules other than `__init__._print_json`. `print(` outside that one helper is a smell.
7. **What we'd want to log if we added logging**: workspace path on first use; git command + cwd + exit code; number of skills scanned; number of drafts proposed. Phrase as "if logging is introduced, add structured events with these fields", not as something the codebase already does.

## Tools Available

GitNexus MCP is configured globally for Codex. Pass `repo: "skill-manager"` on every call — multiple repos are indexed.

### GitNexus MCP

| Tool | Purpose | Example |
|------|---------|---------|
| `gitnexus_query` | Find execution flows by concept | `gitnexus_query({repo: "skill-manager", query: "scan sources and write registry"})` |
| `gitnexus_context` | 360-degree symbol view | `gitnexus_context({repo: "skill-manager", name: "Workspace"})` |
| `gitnexus_impact` | Blast radius | `gitnexus_impact({repo: "skill-manager", target: "write_json", direction: "upstream"})` |
| `gitnexus_cypher` | Raw Cypher | `gitnexus_cypher({repo: "skill-manager", query: "MATCH (f:Function) WHERE f.filePath STARTS WITH 'src/' AND f.name STARTS WITH '_' RETURN f.name, f.filePath LIMIT 50"})` |

Schema labels: `Function`, `Class`, `File`, `Folder`, `Module`, `Community`, `Process`. Edges via `CodeRelation`. There is **no** `Cluster` table.

### ABCoder MCP

Not configured (Python AST analysis is unreliable). Skip it.

### Recommended Workflow

1. **Read first.** Walk every file under `src/skill_manager/`. The whole package is small.
2. **Verify "no logging" by grep**: `grep -RIn 'import logging\|logging\.' src/` should return nothing.
3. **Verify "no custom exceptions"**: `grep -RIn 'class .*Error\|class .*Exception' src/` should also return nothing.
4. **Use GitNexus for verification**, e.g. find every caller of `write_json` to confirm the "all writes go through write_json" claim.
5. **Cite test files** as well as source files — `tests/test_sources.py` and `tests/test_derive_export.py` pin behavior.

## Files to Fill (this task)

You own exactly these files. Do **not** modify anything outside this list.

### `.trellis/spec/backend/state-persistence.md` (NEW — create this)

Write this from scratch. It replaces the template `database-guidelines.md`. Required sections:

- **Overview** — one paragraph: skill-manager has no database; it persists JSON on disk under a `Workspace`. Why: zero deps, easy inspection, git-friendly.
- **Workspace layout** — a tree of `~/.skill-manager/` mirroring `Workspace.__init__`, with one-line role per subdir.
- **JSON I/O conventions** — always `workspace.read_json` / `workspace.write_json`; UTF-8, `ensure_ascii=False`, `indent=2`, parent-dir creation, trailing newline.
- **Schema-tolerant readers** — `_load_sources` / `_load_skills` accept both list and envelope shapes; pattern is "default to []; accept dict[wrapped]; otherwise treat as raw list".
- **Append-only files** — `update-log.json` pattern: read full → append entry → write full. Document that we accept the O(n) rewrite cost in exchange for crash safety + readability.
- **External working trees (git clones)** — `sources/<name>/` is owned by git, mutated only via `_git(...)` subprocess calls; skill-manager never writes inside that subtree.
- **Default workspace + override** — `~/.skill-manager`, `SKILL_MANAGER_HOME`, CLI `--workspace`. Last-one-wins.
- **Provenance is non-optional** — every derived artifact must carry an `Evidence` chain; cite `models.Evidence` shape and the "## Provenance" markdown footer pattern.
- **Anti-patterns** — direct `open()` + `json.load`; `yaml.safe_load` (frontmatter parser is hand-rolled); writing inside `sources/<name>/`; adding a new persisted subdir without extending `Workspace` and `ensure()`.

### `.trellis/spec/backend/error-handling.md`

Replace the template with sections grounded in actual code:

- **Overview** — built-in exceptions only; no custom hierarchy; exceptions used for failure, not control flow.
- **Exception vocabulary** — table of `ValueError` / `KeyError` / `FileNotFoundError` / `subprocess.CalledProcessError`, each with the canonical raise sites (file:line) and a short "when to raise".
- **Argparse error path** — `parser.error(...)` for malformed CLI invocations; auto-exits 2 with stderr usage.
- **Message style** — embed the offending value (`source already exists with different configuration: {name}`); end with the relevant identifier; do not include tracebacks in the message body.
- **Subprocess fallback pattern** — show the `add_source` try/except `CalledProcessError` example.
- **Anti-patterns** — broad `except Exception:` swallows; custom exception subclasses; raising bare strings; logging-then-reraise pairs; using exceptions to skip features.
- **Code review checklist** — points reviewers should hit when accepting new error paths.

### `.trellis/spec/backend/logging-guidelines.md`

Replace the template. Reframe as "structured stdout discipline" since there is no logging library:

- **Overview** — there is no `logging` module usage. Single JSON document per CLI invocation; stderr is reserved for tracebacks.
- **Where output happens** — only in `__init__._print_json` (cite `src/skill_manager/__init__.py:11-13`). Document the indent/ensure_ascii contract.
- **Why no logging library** — zero-dep invariant + script-friendly output. If logging is later introduced, name the candidate (`logging`, stdlib only) and the structured fields to emit (workspace path, git command + cwd + rc, scan counts, draft counts).
- **`print` is forbidden** outside `_print_json`. Verify this by grep before publishing.
- **Sensitive data** — outputs may include git URLs and absolute filesystem paths; warn that exports must not be shipped publicly.
- **Anti-patterns** — `print(...)` for debug; mixed stdout text + JSON; tqdm/rich progress; verbose flags that change the JSON shape.

### Remove the old template

After writing `state-persistence.md`, **delete** `.trellis/spec/backend/database-guidelines.md`. The structure-spec task will update `index.md` to point at the new file.

## Important Rules

### Stay in your lane
- ONLY modify `.trellis/spec/backend/{state-persistence.md, error-handling.md, logging-guidelines.md}` and delete `database-guidelines.md`.
- DO NOT touch `directory-structure.md`, `quality-guidelines.md`, or `index.md` — those belong to `backend-structure-spec`.
- DO NOT modify `src/`, `tests/`, `pyproject.toml`, or any other repo file.
- DO NOT run git commands. Editing tracked files is fine; staging/committing is the human's job.
- You may *read* any file for analysis.

### Adapt the spec to reality
- The template's "ORM / migrations / table naming" sections do not apply — drop them. Replace with the JSON-persistence sections above.
- The template's logging-library questions don't apply — invert them ("we deliberately do not use a logging library because …").
- Add sections the templates miss (provenance, schema-tolerant readers, structured stdout).

### Document reality, not ideals
- Every claim about behavior must be verifiable by reading the code. If your bullet point disagrees with the code, fix the bullet point.
- Run `grep -RIn 'import logging\|logging\.' src/` and `grep -RIn '^class .*Error\b' src/` before locking in "no logging" and "no custom exceptions". If either returns hits, document what you found instead.

## Acceptance Criteria

- [ ] `state-persistence.md` exists and contains a real tree of `~/.skill-manager/` derived from `Workspace.__init__`.
- [ ] `database-guidelines.md` is **deleted**.
- [ ] `error-handling.md` enumerates the four exception types with file:line raise sites.
- [ ] `logging-guidelines.md` documents the "no logging library, single-JSON stdout" rule with a citation to `__init__._print_json`.
- [ ] At least 3 file:line citations per filled spec file.
- [ ] No "(To be filled by the team)" or `<!-- ... -->` HTML-comment prompts left in your files.
- [ ] Substantive length: each filled file ≥ 80 lines.

## Technical Notes

- Package path: `/Users/zhangbowen/Projects/NewTools-Research/skill-manager`
- Source root: `src/skill_manager/`
- Run tests with: `uv run pytest`
- GitNexus index already built; pass `repo: "skill-manager"` on every MCP call.
- The structure-spec task (`05-13-backend-structure-spec`) is updating `index.md` to point at `state-persistence.md`. You do **not** edit `index.md`; just create / delete the right files.
