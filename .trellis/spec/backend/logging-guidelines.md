# Logging Guidelines

> Structured stdout discipline for skill-manager.

---

## Overview

skill-manager does not use a logging library in `src/skill_manager/`. The CLI contract is one successful JSON document on stdout per invocation, produced through `_print_json()`, while malformed CLI invocations and uncaught runtime exceptions use argparse or Python's normal stderr behavior (`src/skill_manager/__init__.py:15`, `src/skill_manager/__init__.py:16`, `src/skill_manager/__init__.py:70`, `src/skill_manager/__init__.py:71`, `src/skill_manager/__init__.py:124`).

Verification before publishing this guide: `rg -n "import logging|logging\\." src/skill_manager` returned no matches, and `rg -n "print\\(" src/skill_manager` returned only `_print_json()` (`src/skill_manager/__init__.py:15`, `src/skill_manager/__init__.py:16`).

---

## Where Output Happens

- Write successful CLI output only through `_print_json(payload)`, which calls `json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2)` and then `print(...)` once (`src/skill_manager/__init__.py:15`, `src/skill_manager/__init__.py:16`).
- Keep command dispatch as return-one-payload control flow; each successful branch calls `_print_json(...)` once and returns immediately (`src/skill_manager/__init__.py:77`, `src/skill_manager/__init__.py:78`, `src/skill_manager/__init__.py:80`, `src/skill_manager/__init__.py:81`, `src/skill_manager/__init__.py:84`, `src/skill_manager/__init__.py:87`, `src/skill_manager/__init__.py:90`, `src/skill_manager/__init__.py:93`).
- Keep the same pattern for derive, project, export, and eval commands; they print one payload and return rather than writing progress messages (`src/skill_manager/__init__.py:99`, `src/skill_manager/__init__.py:100`, `src/skill_manager/__init__.py:102`, `src/skill_manager/__init__.py:103`, `src/skill_manager/__init__.py:106`, `src/skill_manager/__init__.py:109`, `src/skill_manager/__init__.py:112`, `src/skill_manager/__init__.py:115`, `src/skill_manager/__init__.py:118`, `src/skill_manager/__init__.py:121`).
- Convert dataclasses and paths before printing; `to_jsonable()` stringifies `Path`, expands dataclasses, and recurses through lists and dictionaries (`src/skill_manager/models.py:79`, `src/skill_manager/models.py:80`, `src/skill_manager/models.py:82`, `src/skill_manager/models.py:83`, `src/skill_manager/models.py:84`, `src/skill_manager/models.py:86`).
- Keep JSON Unicode-preserving and pretty-printed; the same `ensure_ascii=False` and `indent=2` stdout contract mirrors persisted JSON formatting (`src/skill_manager/__init__.py:16`, `src/skill_manager/workspace.py:50`).

---

## Why There Is No Logging Library

- Preserve the local-first, stdlib-only runtime style already visible in CLI and workspace code; output uses `argparse`, `json`, and `Path`, and persistence uses `json` plus filesystem paths (`src/skill_manager/__init__.py:3`, `src/skill_manager/__init__.py:4`, `src/skill_manager/__init__.py:5`, `src/skill_manager/workspace.py:3`, `src/skill_manager/workspace.py:5`).
- Preserve script-friendly stdout for commands such as `uv run skillmgr scan | jq ...`; `scan` prints a single `{"skills": ...}` object and returns (`src/skill_manager/__init__.py:84`, `src/skill_manager/__init__.py:87`, `src/skill_manager/__init__.py:88`).
- Keep stderr for errors instead of duplicating failures in stdout; `main()` does not catch feature exceptions, and the final unreachable command path uses `parser.error(...)` (`src/skill_manager/__init__.py:69`, `src/skill_manager/__init__.py:71`, `src/skill_manager/__init__.py:74`, `src/skill_manager/__init__.py:78`, `src/skill_manager/__init__.py:124`).
- If logging is introduced later, use only the stdlib `logging` module and keep JSON stdout unchanged; command payloads are already structured dictionaries and dataclasses (`src/skill_manager/__init__.py:15`, `src/skill_manager/__init__.py:16`, `src/skill_manager/models.py:20`, `src/skill_manager/models.py:41`, `src/skill_manager/models.py:67`).

---

## Future Structured Events

If a logging layer is added, emit structured events to stderr or another non-stdout sink so stdout remains a single command result (`src/skill_manager/__init__.py:15`, `src/skill_manager/__init__.py:16`, `src/skill_manager/__init__.py:124`).

- Include the workspace root on first use; `Workspace.__init__` resolves it from the explicit root or default workspace (`src/skill_manager/workspace.py:9`, `src/skill_manager/workspace.py:12`, `src/skill_manager/workspace.py:14`).
- Include git command arguments, cwd, and return status for git operations; `_git()` centralizes command construction, cwd, `check=True`, captured output, and text mode (`src/skill_manager/sources.py:201`, `src/skill_manager/sources.py:202`, `src/skill_manager/sources.py:203`, `src/skill_manager/sources.py:204`, `src/skill_manager/sources.py:205`, `src/skill_manager/sources.py:206`, `src/skill_manager/sources.py:207`, `src/skill_manager/sources.py:208`).
- Include scan counts after source scanning; `scan_sources()` builds a `skills` list and writes it to `registry/skills.json` before returning the list (`src/skill_manager/sources.py:76`, `src/skill_manager/sources.py:79`, `src/skill_manager/sources.py:98`, `src/skill_manager/sources.py:124`, `src/skill_manager/sources.py:125`).
- Include changed source counts and affected draft counts after updates; `update_sources()` appends `changed_skill_ids` and `affected_drafts` to the update log entry when commits change (`src/skill_manager/sources.py:59`, `src/skill_manager/sources.py:60`, `src/skill_manager/sources.py:61`, `src/skill_manager/sources.py:68`, `src/skill_manager/sources.py:69`).
- Include draft counts after derive proposals; `derive.propose()` collects summaries, appends one summary per written draft, and returns the summaries list (`src/skill_manager/derive.py:225`, `src/skill_manager/derive.py:231`, `src/skill_manager/derive.py:233`, `src/skill_manager/derive.py:235`, `src/skill_manager/derive.py:243`, `src/skill_manager/derive.py:245`).
- Include export destination and installed path after export; `export.apply()` returns `target`, installed `path`, and `status` in its JSON payload (`src/skill_manager/export.py:67`, `src/skill_manager/export.py:69`, `src/skill_manager/export.py:72`, `src/skill_manager/export.py:74`, `src/skill_manager/export.py:75`, `src/skill_manager/export.py:76`).

---

## Print Discipline

- Do not add `print(...)` outside `_print_json()`; the only current source print is the one JSON sink in `__init__.py` (`src/skill_manager/__init__.py:15`, `src/skill_manager/__init__.py:16`).
- Do not print progress lines before or after JSON; every CLI branch is shaped as compute payload, `_print_json(payload)`, return (`src/skill_manager/__init__.py:77`, `src/skill_manager/__init__.py:78`, `src/skill_manager/__init__.py:80`, `src/skill_manager/__init__.py:81`, `src/skill_manager/__init__.py:87`, `src/skill_manager/__init__.py:88`, `src/skill_manager/__init__.py:115`, `src/skill_manager/__init__.py:116`).
- Do not print from library modules; feature modules return dataclasses, lists, or dictionaries to the CLI boundary instead (`src/skill_manager/sources.py:40`, `src/skill_manager/sources.py:73`, `src/skill_manager/sources.py:125`, `src/skill_manager/derive.py:245`, `src/skill_manager/project.py:117`, `src/skill_manager/export.py:72`, `src/skill_manager/evals.py:52`).
- Do not add `tqdm`, `rich`, spinners, or other progress UIs to command stdout; `subprocess.run()` already captures git stdout in `_git()` instead of streaming it (`src/skill_manager/sources.py:202`, `src/skill_manager/sources.py:205`, `src/skill_manager/sources.py:206`, `src/skill_manager/sources.py:209`).

---

## Sensitive Data

- Treat stdout as local diagnostic data, not a public artifact; source add returns `SourceRecord`, which includes the git URL and commit that `_print_json()` serializes (`src/skill_manager/models.py:20`, `src/skill_manager/models.py:23`, `src/skill_manager/models.py:26`, `src/skill_manager/sources.py:37`, `src/skill_manager/sources.py:40`, `src/skill_manager/__init__.py:77`, `src/skill_manager/__init__.py:78`).
- Project proposals may expose absolute project paths because `project_root` is resolved and then included in evidence, provenance, and returned paths (`src/skill_manager/project.py:59`, `src/skill_manager/project.py:96`, `src/skill_manager/project.py:107`, `src/skill_manager/project.py:108`, `src/skill_manager/project.py:120`, `src/skill_manager/project.py:121`, `src/skill_manager/project.py:122`).
- Exports may expose absolute filesystem paths because export destinations can be user supplied or host defaults, and the returned payload contains the installed `SKILL.md` path (`src/skill_manager/export.py:10`, `src/skill_manager/export.py:28`, `src/skill_manager/export.py:35`, `src/skill_manager/export.py:67`, `src/skill_manager/export.py:69`, `src/skill_manager/export.py:75`).
- Do not paste or publish command output blindly when git URLs, project paths, or export paths are sensitive; those values are intentionally returned for local automation (`src/skill_manager/__init__.py:15`, `src/skill_manager/__init__.py:16`, `src/skill_manager/models.py:79`, `src/skill_manager/models.py:80`, `src/skill_manager/models.py:86`).

---

## Command Payload Shapes

- Keep source-add output as the serialized `SourceRecord`; the command prints the return value from `add_source()` directly (`src/skill_manager/__init__.py:77`, `src/skill_manager/__init__.py:78`, `src/skill_manager/sources.py:37`, `src/skill_manager/sources.py:40`).
- Keep source-update output wrapped as `{"changed": [...]}`; `main()` creates that object and `update_sources()` returns the changed source names (`src/skill_manager/__init__.py:80`, `src/skill_manager/__init__.py:81`, `src/skill_manager/sources.py:43`, `src/skill_manager/sources.py:50`, `src/skill_manager/sources.py:73`).
- Keep scan output wrapped as `{"skills": [...]}`; `scan_sources()` returns the scanned skill list after writing `registry/skills.json` (`src/skill_manager/__init__.py:84`, `src/skill_manager/__init__.py:87`, `src/skill_manager/sources.py:76`, `src/skill_manager/sources.py:124`, `src/skill_manager/sources.py:125`).
- Keep routing output wrapped as `{"candidates": [...]}`; `route()` returns ordered candidates and `main()` does not add progress or warnings around that object (`src/skill_manager/__init__.py:90`, `src/skill_manager/__init__.py:93`, `src/skill_manager/routing.py:54`, `src/skill_manager/routing.py:55`).
- Keep derive proposal output wrapped as `{"drafts": [...]}` and approval output as the approval summary dictionary; both are printed once by `main()` (`src/skill_manager/__init__.py:99`, `src/skill_manager/__init__.py:100`, `src/skill_manager/__init__.py:102`, `src/skill_manager/__init__.py:103`, `src/skill_manager/derive.py:245`, `src/skill_manager/derive.py:268`).
- Keep eval output as the metrics dictionary returned by `evals.run()`; the result includes row counts, hit and recall metrics, false-positive-like count, and details (`src/skill_manager/__init__.py:118`, `src/skill_manager/__init__.py:121`, `src/skill_manager/evals.py:52`, `src/skill_manager/evals.py:53`, `src/skill_manager/evals.py:56`, `src/skill_manager/evals.py:57`, `src/skill_manager/evals.py:59`, `src/skill_manager/evals.py:60`).

---

## Anti-Patterns

- Do not mix human text and JSON on stdout; `_print_json()` is the only stdout writer and it writes one JSON document (`src/skill_manager/__init__.py:15`, `src/skill_manager/__init__.py:16`).
- Do not add debug `print(...)` calls in feature modules; return structured data to `main()` instead (`src/skill_manager/__init__.py:74`, `src/skill_manager/__init__.py:78`, `src/skill_manager/__init__.py:84`, `src/skill_manager/__init__.py:87`, `src/skill_manager/__init__.py:112`, `src/skill_manager/__init__.py:115`).
- Do not make verbose flags change the shape of command JSON; routing, evals, scan, export, and derive return fixed dictionary or dataclass-shaped payloads (`src/skill_manager/__init__.py:87`, `src/skill_manager/__init__.py:93`, `src/skill_manager/__init__.py:100`, `src/skill_manager/__init__.py:115`, `src/skill_manager/__init__.py:121`).
- Do not stream git output to stdout; `_git()` captures subprocess stdout and returns a stripped string to callers (`src/skill_manager/sources.py:202`, `src/skill_manager/sources.py:206`, `src/skill_manager/sources.py:207`, `src/skill_manager/sources.py:209`).
- Do not log an exception and then re-raise it from command dispatch; uncaught feature exceptions already produce one stderr failure path, and parser validation uses `parser.error(...)` (`src/skill_manager/__init__.py:69`, `src/skill_manager/__init__.py:71`, `src/skill_manager/__init__.py:124`).
