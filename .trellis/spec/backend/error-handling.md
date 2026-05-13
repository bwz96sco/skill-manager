# Error Handling

> Runtime failure conventions for skill-manager.

---

## Overview

skill-manager uses standard Python exceptions at module boundaries instead of a project-specific exception hierarchy. The package raises `ValueError`, `KeyError`, `FileNotFoundError`, and lets `subprocess.CalledProcessError` propagate from git commands; callers normally do not catch these failures, so the CLI exits non-zero and Python or argparse writes diagnostics to stderr (`src/skill_manager/sources.py:28`, `src/skill_manager/sources.py:53`, `src/skill_manager/project.py:61`, `src/skill_manager/export.py:57`, `src/skill_manager/sources.py:202`, `src/skill_manager/sources.py:205`).

---

## Exception Vocabulary

| Exception | Canonical raise or source site | When to raise |
|---|---|---|
| `ValueError` | `add_source()` rejects changed config for an existing source (`src/skill_manager/sources.py:24`, `src/skill_manager/sources.py:26`, `src/skill_manager/sources.py:28`). | Raise when a caller supplied a syntactically valid identifier but its requested state conflicts with existing workspace state. |
| `ValueError` | `_destination()` rejects missing project destinations and unknown export targets (`src/skill_manager/export.py:28`, `src/skill_manager/export.py:31`, `src/skill_manager/export.py:33`, `src/skill_manager/export.py:34`). | Raise when an option value is invalid for the chosen operation. |
| `ValueError` | `export.apply()` rejects malformed approved JSON, unapproved drafts, and non-generated drafts (`src/skill_manager/export.py:59`, `src/skill_manager/export.py:61`, `src/skill_manager/export.py:62`, `src/skill_manager/export.py:63`, `src/skill_manager/export.py:64`, `src/skill_manager/export.py:65`). | Raise when a persisted object exists but violates the operation contract. |
| `ValueError` | `derive.approve()` rejects draft JSON that is not an object (`src/skill_manager/derive.py:255`, `src/skill_manager/derive.py:256`, `src/skill_manager/derive.py:257`). | Raise when a persisted payload shape is wrong and cannot be repaired safely. |
| `KeyError` | `update_sources()` raises for an unknown selected source (`src/skill_manager/sources.py:49`, `src/skill_manager/sources.py:51`, `src/skill_manager/sources.py:52`, `src/skill_manager/sources.py:53`). | Raise when a lookup by name fails and the missing name is the useful diagnostic. |
| `FileNotFoundError` | `project.propose()` rejects a missing project directory (`src/skill_manager/project.py:57`, `src/skill_manager/project.py:59`, `src/skill_manager/project.py:60`, `src/skill_manager/project.py:61`). | Raise when a required filesystem input path is absent or is not the expected kind. |
| `FileNotFoundError` | `project.propose()` rejects projects with none of `README.md`, `AGENTS.md`, or `CLAUDE.md` (`src/skill_manager/project.py:11`, `src/skill_manager/project.py:63`, `src/skill_manager/project.py:64`, `src/skill_manager/project.py:75`, `src/skill_manager/project.py:76`). | Raise when a directory exists but lacks the required guidance files. |
| `FileNotFoundError` | `derive.approve()` rejects missing draft JSON or Markdown (`src/skill_manager/derive.py:250`, `src/skill_manager/derive.py:251`, `src/skill_manager/derive.py:252`, `src/skill_manager/derive.py:253`). | Raise when approval needs a draft pair and either side is absent. |
| `FileNotFoundError` | `export.apply()` rejects missing approved generated artifacts (`src/skill_manager/export.py:54`, `src/skill_manager/export.py:55`, `src/skill_manager/export.py:56`, `src/skill_manager/export.py:57`). | Raise when export needs an approved JSON and Markdown pair and either side is absent. |
| `subprocess.CalledProcessError` | `_git()` invokes `subprocess.run(..., check=True, capture_output=True, text=True)` (`src/skill_manager/sources.py:201`, `src/skill_manager/sources.py:202`, `src/skill_manager/sources.py:203`, `src/skill_manager/sources.py:205`, `src/skill_manager/sources.py:206`, `src/skill_manager/sources.py:207`). | Let it propagate when git fails, except for the explicit clone fallback described below. |

---

## Argparse Error Path

- Let argparse own malformed CLI invocation failures; `build_parser()` marks the top-level subcommand and nested subcommands as required, and `parse_args()` is called before dispatch (`src/skill_manager/__init__.py:25`, `src/skill_manager/__init__.py:28`, `src/skill_manager/__init__.py:45`, `src/skill_manager/__init__.py:56`, `src/skill_manager/__init__.py:63`, `src/skill_manager/__init__.py:70`, `src/skill_manager/__init__.py:71`).
- Keep CLI validation in parser declarations when argparse can express it; export target choices are declared on the argument instead of validated later in command dispatch (`src/skill_manager/__init__.py:57`, `src/skill_manager/__init__.py:58`, `src/skill_manager/__init__.py:59`).
- Use `parser.error(...)` only for dispatch states that should be unreachable after parser validation; the current fallback is `parser.error("Unhandled command")` at the end of `main()` (`src/skill_manager/__init__.py:118`, `src/skill_manager/__init__.py:121`, `src/skill_manager/__init__.py:124`).
- Do not wrap argparse errors into JSON; malformed invocations should keep argparse's standard stderr usage output and exit status 2, while successful dispatch returns JSON through `_print_json()` (`src/skill_manager/__init__.py:15`, `src/skill_manager/__init__.py:16`, `src/skill_manager/__init__.py:77`, `src/skill_manager/__init__.py:78`, `src/skill_manager/__init__.py:124`).

---

## Message Style

- Include the offending value in the message and usually end with that value; `add_source()` ends its conflict message with the source name (`src/skill_manager/sources.py:24`, `src/skill_manager/sources.py:28`).
- Quote draft IDs and export targets with `!r` when the identifier may contain spaces or punctuation; export and derive both use that style (`src/skill_manager/export.py:34`, `src/skill_manager/export.py:57`, `src/skill_manager/export.py:61`, `src/skill_manager/export.py:63`, `src/skill_manager/export.py:65`, `src/skill_manager/derive.py:253`, `src/skill_manager/derive.py:257`).
- Include useful filesystem context for path-based failures; project and export errors name the project root or derived directory (`src/skill_manager/project.py:61`, `src/skill_manager/project.py:76`, `src/skill_manager/export.py:57`).
- Do not include tracebacks in exception message strings; Python prints tracebacks for uncaught exceptions, while the code messages stay short identifiers plus context (`src/skill_manager/export.py:63`, `src/skill_manager/export.py:65`, `src/skill_manager/sources.py:53`).

---

## Subprocess Fallback Pattern

- Use the explicit downgrade pattern only when a better git command has a known fallback; `add_source()` first tries `git clone --branch <ref>` and, only on `subprocess.CalledProcessError`, retries a plain clone followed by `git checkout <ref>` (`src/skill_manager/sources.py:30`, `src/skill_manager/sources.py:31`, `src/skill_manager/sources.py:32`, `src/skill_manager/sources.py:33`, `src/skill_manager/sources.py:34`, `src/skill_manager/sources.py:35`).
- Keep fallback exceptions narrow; the checkout fallback catches only `subprocess.CalledProcessError`, while frontmatter scalar decoding catches only `json.JSONDecodeError` for JSON-like literals (`src/skill_manager/sources.py:33`, `src/skill_manager/frontmatter.py:17`, `src/skill_manager/frontmatter.py:18`, `src/skill_manager/frontmatter.py:19`, `src/skill_manager/frontmatter.py:24`, `src/skill_manager/frontmatter.py:25`, `src/skill_manager/frontmatter.py:26`).
- Let git failures propagate everywhere else; `update_sources()` calls `_git(["pull", "--ff-only"], cwd=checkout)` with no catch, and `_commit()` also delegates to `_git()` (`src/skill_manager/sources.py:55`, `src/skill_manager/sources.py:56`, `src/skill_manager/sources.py:57`, `src/skill_manager/sources.py:212`, `src/skill_manager/sources.py:213`).

---

## Error Propagation

- Fail at the boundary that has enough context to name the problem; `update_sources()` raises before calling git for an unknown selected source, and `project.propose()` raises before writing a draft when project guidance is missing (`src/skill_manager/sources.py:51`, `src/skill_manager/sources.py:52`, `src/skill_manager/sources.py:53`, `src/skill_manager/project.py:75`, `src/skill_manager/project.py:76`).
- Prefer ordinary return paths for valid idempotent states; `add_source()` returns an existing source only when URL, skill root, ref, and destination all match (`src/skill_manager/sources.py:24`, `src/skill_manager/sources.py:25`, `src/skill_manager/sources.py:26`, `src/skill_manager/sources.py:27`).
- Do not catch module exceptions in `main()`; command branches call the feature function, print successful payloads, and return, leaving failures to Python's standard stderr path (`src/skill_manager/__init__.py:74`, `src/skill_manager/__init__.py:77`, `src/skill_manager/__init__.py:78`, `src/skill_manager/__init__.py:80`, `src/skill_manager/__init__.py:81`, `src/skill_manager/__init__.py:112`, `src/skill_manager/__init__.py:115`).
- Keep tolerant parsing separate from error signaling; registry readers return empty lists for non-list wrapper values, while operation commands still raise for invalid user-selected IDs or missing artifacts (`src/skill_manager/routing.py:65`, `src/skill_manager/routing.py:70`, `src/skill_manager/routing.py:71`, `src/skill_manager/evals.py:65`, `src/skill_manager/evals.py:70`, `src/skill_manager/evals.py:71`, `src/skill_manager/sources.py:53`, `src/skill_manager/export.py:57`).

---

## Test-Asserted Contracts

- Preserve `KeyError` for unknown source updates; `tests/test_sources.py` asserts that exact exception family (`tests/test_sources.py:89`, `tests/test_sources.py:96`, `tests/test_sources.py:97`).
- Preserve `ValueError` for unapproved generated draft export; the test matches the phrase `not approved` (`tests/test_derive_export.py:97`, `tests/test_derive_export.py:108`, `tests/test_derive_export.py:109`).
- Preserve `FileNotFoundError` for missing approved export artifacts; the test calls `export.apply("missing", ...)` under `pytest.raises(FileNotFoundError)` (`tests/test_derive_export.py:111`, `tests/test_derive_export.py:112`).
- Preserve `ValueError` for raw or non-generated drafts and missing explicit project destinations; both behaviors are asserted in export tests (`tests/test_derive_export.py:120`, `tests/test_derive_export.py:121`, `tests/test_derive_export.py:123`, `tests/test_derive_export.py:124`).

---

## Anti-Patterns

- Do not add custom exception subclasses unless there is a concrete caller that can handle them differently; current contracts are built on Python built-ins and subprocess errors (`src/skill_manager/sources.py:28`, `src/skill_manager/sources.py:53`, `src/skill_manager/project.py:61`, `src/skill_manager/export.py:57`, `src/skill_manager/sources.py:202`, `src/skill_manager/sources.py:205`).
- Do not use broad `except Exception:` blocks; current catches are specific fallback or scalar-decoding catches (`src/skill_manager/sources.py:33`, `src/skill_manager/frontmatter.py:19`, `src/skill_manager/frontmatter.py:26`).
- Do not raise bare strings or opaque messages; current raises include the selected source, target, draft ID, project root, or derived directory (`src/skill_manager/sources.py:28`, `src/skill_manager/export.py:34`, `src/skill_manager/export.py:57`, `src/skill_manager/project.py:61`, `src/skill_manager/project.py:76`).
- Do not log and re-raise; there is no module logging path, and CLI command failures should surface once through Python or argparse stderr (`src/skill_manager/__init__.py:15`, `src/skill_manager/__init__.py:16`, `src/skill_manager/__init__.py:124`).
- Do not use exceptions to skip optional features; readers should return empty collections for absent optional data, as registry and eval loaders do (`src/skill_manager/workspace.py:42`, `src/skill_manager/workspace.py:43`, `src/skill_manager/workspace.py:44`, `src/skill_manager/routing.py:70`, `src/skill_manager/routing.py:71`, `src/skill_manager/evals.py:70`, `src/skill_manager/evals.py:71`).

---

## Code Review Checklist

- Does the new error use one of the existing exception families unless a caller needs a new type (`src/skill_manager/sources.py:28`, `src/skill_manager/sources.py:53`, `src/skill_manager/project.py:61`, `src/skill_manager/export.py:57`)?
- Does the message include the offending source name, draft ID, target, or path like the existing raise sites (`src/skill_manager/sources.py:28`, `src/skill_manager/export.py:34`, `src/skill_manager/export.py:63`, `src/skill_manager/project.py:76`)?
- Is any `except` clause narrow and justified by a fallback or tolerant parser behavior (`src/skill_manager/sources.py:33`, `src/skill_manager/frontmatter.py:19`, `src/skill_manager/frontmatter.py:26`)?
- Does CLI input validation belong in argparse choices or required arguments instead of manual dispatch code (`src/skill_manager/__init__.py:25`, `src/skill_manager/__init__.py:45`, `src/skill_manager/__init__.py:59`, `src/skill_manager/__init__.py:63`)?
- Do tests assert the public exception type or message when the behavior is user-visible, matching existing source and export tests (`tests/test_sources.py:96`, `tests/test_derive_export.py:108`, `tests/test_derive_export.py:111`, `tests/test_derive_export.py:120`, `tests/test_derive_export.py:123`)?
