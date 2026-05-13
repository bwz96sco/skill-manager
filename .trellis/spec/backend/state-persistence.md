# State Persistence

> Runtime state conventions for skill-manager.

---

## Overview

skill-manager has no database layer. Runtime state is JSON and Markdown on disk under a `Workspace`, which keeps the tool dependency-free, easy to inspect with ordinary shell tools, and friendly to git diffs when users copy or archive workspace files. The authoritative schema starts in `Workspace.__init__`, where a root path is expanded and the well-known directories are assigned, and `Workspace.ensure()` creates those directories before mutating features run (`src/skill_manager/workspace.py:12`, `src/skill_manager/workspace.py:14`, `src/skill_manager/workspace.py:15`, `src/skill_manager/workspace.py:23`).

---

## Workspace Layout

The default root is `~/.skill-manager`, unless `SKILL_MANAGER_HOME` supplies another default or the caller passes an explicit workspace root (`src/skill_manager/workspace.py:9`, `src/skill_manager/workspace.py:14`).

```text
~/.skill-manager/
|-- sources/
|   `-- <name>/                  # git checkout for a subscribed skill source
|-- registry/
|   |-- sources.json             # subscribed SourceRecord rows
|   |-- skills.json              # scanned SkillRecord rows
|   `-- update-log.json          # append-style source update events
|-- drafts/
|   |-- <draft_id>.json          # unapproved generated draft payload
|   `-- <draft_id>.md            # unapproved generated draft markdown
|-- derived/
|   |-- <draft_id>.json          # approved generated draft payload
|   `-- <draft_id>.md            # approved generated draft markdown
|-- exports/                     # reserved workspace-owned export area
|-- evals/
|   `-- goldens.json             # routing golden queries
`-- index/                       # reserved for future indexes
```

- Keep `sources/<name>/` as the checkout root returned by `_source_dir`; it is computed from `workspace.sources` plus the source name (`src/skill_manager/workspace.py:15`, `src/skill_manager/sources.py:134`, `src/skill_manager/sources.py:135`).
- Store source subscriptions in `registry/sources.json`; `_load_sources()` reads that file and `_write_sources()` rewrites it in sorted source-name order (`src/skill_manager/sources.py:138`, `src/skill_manager/sources.py:139`, `src/skill_manager/sources.py:160`, `src/skill_manager/sources.py:161`).
- Store scanned skills in `registry/skills.json`; `scan_sources()` writes the complete skill list after reading each subscribed checkout (`src/skill_manager/sources.py:76`, `src/skill_manager/sources.py:80`, `src/skill_manager/sources.py:85`, `src/skill_manager/sources.py:124`).
- Store source update events in `registry/update-log.json`; `_append_update_log()` owns the read, append, rewrite cycle for that file (`src/skill_manager/sources.py:193`, `src/skill_manager/sources.py:194`, `src/skill_manager/sources.py:195`, `src/skill_manager/sources.py:198`).
- Store unapproved generated skills in `drafts/<draft_id>.json` and `drafts/<draft_id>.md`; both derive and project proposal paths write there (`src/skill_manager/derive.py:231`, `src/skill_manager/derive.py:232`, `src/skill_manager/project.py:111`, `src/skill_manager/project.py:112`).
- Store approved generated skills in `derived/<draft_id>.json` and `derived/<draft_id>.md`; approval writes JSON and copies the approved Markdown into that directory (`src/skill_manager/derive.py:262`, `src/skill_manager/derive.py:263`, `src/skill_manager/derive.py:264`, `src/skill_manager/derive.py:266`).
- Treat `exports/` as reserved workspace-owned state; the directory is declared and created even though current export targets install to host or explicit destinations (`src/skill_manager/workspace.py:20`, `src/skill_manager/workspace.py:30`, `src/skill_manager/export.py:10`, `src/skill_manager/export.py:35`).
- Store routing goldens in `evals/goldens.json`; the eval runner reads that file through `read_json()` and accepts an empty default (`src/skill_manager/workspace.py:21`, `src/skill_manager/evals.py:64`, `src/skill_manager/evals.py:65`).
- Keep `index/` reserved until an implementation writes to it; `Workspace` declares it and `ensure()` creates it, but the current source tree has no writer for it (`src/skill_manager/workspace.py:17`, `src/skill_manager/workspace.py:27`).

---

## JSON I/O Conventions

- Use `workspace.read_json(path, default)` for persisted JSON reads so missing files produce the caller's explicit default (`src/skill_manager/workspace.py:42`, `src/skill_manager/workspace.py:43`, `src/skill_manager/workspace.py:44`).
- Use `workspace.write_json(path, payload)` for persisted JSON writes so parent directories are created and every file is UTF-8 JSON with `ensure_ascii=False`, `indent=2`, and a trailing newline (`src/skill_manager/workspace.py:48`, `src/skill_manager/workspace.py:49`, `src/skill_manager/workspace.py:50`).
- Convert dataclasses and `Path` values through `to_jsonable()` before writing CLI-facing or persisted payloads; it stringifies paths, expands dataclasses through `asdict`, and recurses through lists and dictionaries (`src/skill_manager/models.py:79`, `src/skill_manager/models.py:80`, `src/skill_manager/models.py:82`, `src/skill_manager/models.py:84`, `src/skill_manager/models.py:86`).
- Keep JSON registry writes whole-file and deterministic; `scan_sources()` writes the whole scanned list, and `_write_sources()` sorts source names before writing (`src/skill_manager/sources.py:124`, `src/skill_manager/sources.py:160`, `src/skill_manager/sources.py:161`).
- Markdown artifacts may use `Path.write_text()` directly because they are not JSON state; derive and project proposals write `.md` files beside their `.json` records (`src/skill_manager/derive.py:234`, `src/skill_manager/derive.py:242`, `src/skill_manager/project.py:115`).

---

## Schema-Tolerant Readers

- New registry readers should default to an empty list and accept both raw lists and wrapped dictionaries, matching `_load_sources()` and `_load_skills()` (`src/skill_manager/sources.py:139`, `src/skill_manager/sources.py:141`, `src/skill_manager/sources.py:142`, `src/skill_manager/routing.py:65`, `src/skill_manager/routing.py:66`, `src/skill_manager/routing.py:67`).
- When a wrapped value is not a list, return an empty collection rather than crashing; `_source_skill_ids()`, `_load_skills()`, and `_load_rows()` already use that fail-closed pattern (`src/skill_manager/sources.py:166`, `src/skill_manager/sources.py:167`, `src/skill_manager/sources.py:168`, `src/skill_manager/routing.py:70`, `src/skill_manager/routing.py:71`, `src/skill_manager/evals.py:70`, `src/skill_manager/evals.py:71`).
- Keep backward compatibility for alternate wrappers already supported by code; routing accepts `{"skills": [...]}` and `{"rows": [...]}`, while derive accepts a raw list, `{"skills": [...]}`, or a dictionary of skill objects (`src/skill_manager/routing.py:66`, `src/skill_manager/routing.py:67`, `src/skill_manager/derive.py:49`, `src/skill_manager/derive.py:52`, `src/skill_manager/derive.py:53`, `src/skill_manager/derive.py:56`).

---

## Append-Only Files

- Append-style JSON files use read full, mutate in memory, write full; `_append_update_log()` reads `update-log.json`, normalizes non-lists to `[]`, appends one entry, and rewrites the complete JSON file (`src/skill_manager/sources.py:193`, `src/skill_manager/sources.py:195`, `src/skill_manager/sources.py:196`, `src/skill_manager/sources.py:197`, `src/skill_manager/sources.py:198`).
- Accept the O(n) rewrite cost for small local logs because the resulting JSON remains easy to inspect and the write path retains the same parent-directory and formatting guarantees as other persisted JSON (`src/skill_manager/workspace.py:48`, `src/skill_manager/workspace.py:49`, `src/skill_manager/workspace.py:50`, `src/skill_manager/sources.py:198`).
- Update-log entries should preserve the source name, before and after commits, changed skill IDs, and affected drafts, matching the payload assembled by `update_sources()` (`src/skill_manager/sources.py:61`, `src/skill_manager/sources.py:65`, `src/skill_manager/sources.py:66`, `src/skill_manager/sources.py:67`, `src/skill_manager/sources.py:68`, `src/skill_manager/sources.py:69`).

---

## External Working Trees

- Treat `sources/<name>/` as git-owned state; `add_source()` creates it with `git clone`, and `update_sources()` mutates it with `git pull --ff-only` (`src/skill_manager/sources.py:30`, `src/skill_manager/sources.py:32`, `src/skill_manager/sources.py:34`, `src/skill_manager/sources.py:56`).
- Do not write skill-manager metadata inside the checkout; `scan_sources()` reads `SKILL.md` files and writes only `registry/skills.json`, and the test suite asserts the checkout remains clean after scanning (`src/skill_manager/sources.py:85`, `src/skill_manager/sources.py:87`, `src/skill_manager/sources.py:124`, `tests/test_sources.py:48`, `tests/test_sources.py:64`).
- Run git through `_git()` so command arguments, cwd, `check=True`, captured output, and text mode stay centralized (`src/skill_manager/sources.py:201`, `src/skill_manager/sources.py:202`, `src/skill_manager/sources.py:203`, `src/skill_manager/sources.py:204`, `src/skill_manager/sources.py:205`, `src/skill_manager/sources.py:206`, `src/skill_manager/sources.py:207`).

---

## Default Workspace And Overrides

- The default workspace is `~/.skill-manager`, with `SKILL_MANAGER_HOME` allowed to change that default before `Workspace` is constructed (`src/skill_manager/workspace.py:9`).
- A CLI `--workspace` value wins over the environment default because `main()` passes `args.workspace` into feature calls, and `Workspace.__init__` uses the explicit root when provided (`src/skill_manager/__init__.py:11`, `src/skill_manager/__init__.py:12`, `src/skill_manager/__init__.py:71`, `src/skill_manager/__init__.py:72`, `src/skill_manager/workspace.py:14`).
- Mutating feature modules should normalize with a local `_workspace()` helper and call `ensure()` before writes; sources, derive, project, and export all do this (`src/skill_manager/sources.py:128`, `src/skill_manager/sources.py:130`, `src/skill_manager/derive.py:35`, `src/skill_manager/derive.py:40`, `src/skill_manager/project.py:14`, `src/skill_manager/project.py:19`, `src/skill_manager/export.py:19`, `src/skill_manager/export.py:24`).
- Read-only modules may skip `ensure()` when they only need tolerant reads; routing constructs a `Workspace` and then reads `registry/skills.json` with a default empty list (`src/skill_manager/routing.py:18`, `src/skill_manager/routing.py:64`, `src/skill_manager/routing.py:65`).

---

## Provenance Is Non-Optional

- Every `Evidence` record must carry source, skill ID, path, commit, line range, chunk hash, and text, matching the dataclass contract (`src/skill_manager/models.py:29`, `src/skill_manager/models.py:31`, `src/skill_manager/models.py:32`, `src/skill_manager/models.py:33`, `src/skill_manager/models.py:34`, `src/skill_manager/models.py:35`, `src/skill_manager/models.py:36`, `src/skill_manager/models.py:37`, `src/skill_manager/models.py:38`).
- Scanned skills should include evidence when a non-empty `SKILL.md` body exists; `_evidence_for_body()` computes source metadata, line numbers, a chunk digest, and the source text (`src/skill_manager/sources.py:90`, `src/skill_manager/sources.py:121`, `src/skill_manager/sources.py:283`, `src/skill_manager/sources.py:297`, `src/skill_manager/sources.py:304`, `src/skill_manager/sources.py:305`).
- Generated meta-skill drafts must preserve evidence from source skills and render a `## Provenance` footer in Markdown (`src/skill_manager/derive.py:161`, `src/skill_manager/derive.py:163`, `src/skill_manager/derive.py:177`, `src/skill_manager/derive.py:189`, `src/skill_manager/derive.py:192`, `src/skill_manager/derive.py:196`).
- Generated project skills must record project file provenance in both JSON and Markdown (`src/skill_manager/project.py:51`, `src/skill_manager/project.py:52`, `src/skill_manager/project.py:92`, `src/skill_manager/project.py:96`, `src/skill_manager/project.py:108`, `src/skill_manager/project.py:122`).
- Tests assert provenance survives proposal, approval, and export paths, so new persistence code should not drop those fields (`tests/test_sources.py:59`, `tests/test_sources.py:60`, `tests/test_sources.py:63`, `tests/test_derive_export.py:55`, `tests/test_derive_export.py:57`, `tests/test_derive_export.py:93`).

---

## Anti-Patterns

- Do not use direct `open()` plus `json.load()` for workspace state; route all persisted JSON through `read_json()` and `write_json()` so defaults and formatting remain consistent (`src/skill_manager/workspace.py:42`, `src/skill_manager/workspace.py:48`, `src/skill_manager/sources.py:139`, `src/skill_manager/sources.py:161`).
- Do not introduce `yaml.safe_load()` for `SKILL.md` frontmatter; this project intentionally uses a small hand-rolled frontmatter parser with `read_text()` and scalar decoding (`src/skill_manager/frontmatter.py:9`, `src/skill_manager/frontmatter.py:31`, `src/skill_manager/frontmatter.py:32`, `src/skill_manager/frontmatter.py:47`, `src/skill_manager/frontmatter.py:58`).
- Do not write inside `sources/<name>/` except through git commands; `scan_sources()` reads checkout files and writes registry state elsewhere, and the checkout-clean test makes that behavior contractual (`src/skill_manager/sources.py:85`, `src/skill_manager/sources.py:87`, `src/skill_manager/sources.py:124`, `tests/test_sources.py:64`).
- Do not add a persisted subdirectory without extending both `Workspace.__init__` and `Workspace.ensure()`; otherwise feature code will not have a single schema source or a consistent creation path (`src/skill_manager/workspace.py:12`, `src/skill_manager/workspace.py:15`, `src/skill_manager/workspace.py:21`, `src/skill_manager/workspace.py:23`, `src/skill_manager/workspace.py:32`).
- Do not store non-provenanced generated artifacts; draft JSON and Markdown paths are useful only when they can be traced back to source skills or project guidance (`src/skill_manager/models.py:29`, `src/skill_manager/derive.py:189`, `src/skill_manager/project.py:92`, `tests/test_derive_export.py:57`, `tests/test_derive_export.py:93`).
