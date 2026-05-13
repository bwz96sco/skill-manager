# Backend Development Guidelines

> **Purpose**: Explain how backend code is organized, persisted, reviewed, and operated in this project.

---

## Why Backend Guidelines?

`skill-manager` is not a web backend. It is a local-first Python CLI package
that stores JSON files under a workspace, routes natural-language tasks to
skills, proposes generated skill drafts, and exports approved generated drafts.

These guides keep future changes aligned with the actual implementation:

- Flat Python package, not layered service folders.
- Filesystem JSON persistence, not a database or ORM.
- Argparse CLI output as one JSON document per command.
- Stdlib-only runtime code.
- Pytest coverage built around temporary workspace directories.

---

## Available Guides

| Guide | Purpose | File | Status |
|-------|---------|------|--------|
| [Directory Structure](./directory-structure.md) | Where backend code lives, where new modules belong, and how the flat package is organized. | `./directory-structure.md` | Filled |
| [Quality Guidelines](./quality-guidelines.md) | Required patterns, forbidden patterns, test expectations, and CLI output discipline. | `./quality-guidelines.md` | Filled |
| [State Persistence](./state-persistence.md) | Workspace directories, JSON files, registry state, drafts, exports, and eval storage. | `./state-persistence.md` | Filled |
| [Error Handling](./error-handling.md) | Exception style, CLI failure behavior, missing file handling, and invalid-state handling. | `./error-handling.md` | Filled |
| [Logging Guidelines](./logging-guidelines.md) | Current no-logging stance and how to preserve JSON stdout behavior. | `./logging-guidelines.md` | Filled |

`database-guidelines.md` has been superseded by `state-persistence.md`. The
project has no database layer; persistent state is JSON on disk through
`Workspace` and the helpers in `src/skill_manager/workspace.py:13-50`.

---

## Quick Reference

### When Adding A CLI Feature

- Put implementation code in a focused module under `src/skill_manager/`.
- Add argparse wiring in `build_parser()`.
- Add a lazy import in the matching `main()` dispatch branch.
- Return Python objects from the feature module.
- Let `_print_json()` handle stdout serialization.

See `src/skill_manager/__init__.py:19-66` for parser setup and
`src/skill_manager/__init__.py:69-124` for command dispatch.

### When Adding Workspace State

- Read the State Persistence guide first.
- Add any new directory attribute in `Workspace.__init__`.
- Add the same path to the `ensure()` tuple.
- Use `read_json()` and `write_json()` for JSON files.
- Keep generated Markdown writes in draft-producing modules.

See `src/skill_manager/workspace.py:13-50`,
`src/skill_manager/derive.py:233-242`, and
`src/skill_manager/project.py:113-115`.

### When Adding Routing Logic

- Reuse `text.py` helpers for normalization, tokenization, cosine similarity,
  keyword hits, and digesting.
- Keep exact-match and lexical scoring reasons explanatory.
- Update tests for exact reason strings and multilingual behavior.

See `src/skill_manager/text.py:10-46`,
`src/skill_manager/routing.py:123-168`, and
`tests/test_routing.py:73-145`.

### When Adding Source-Scanning Logic

- Keep git command execution inside `sources._git()`.
- Keep `SKILL.md` metadata parsing in `frontmatter.py`.
- Keep inferred tags and aliases in `sources.py`.
- Persist registry updates through workspace JSON helpers.

See `src/skill_manager/sources.py:76-125`,
`src/skill_manager/sources.py:201-280`, and
`src/skill_manager/frontmatter.py:31-68`.

### When Adding Tests

- Use pytest.
- Use `tmp_path` for workspace isolation.
- Keep tests flat under `tests/test_<module>.py`.
- Assert public behavior and persisted outputs.
- Add multilingual fixtures when text matching changes.

See `tests/test_sources.py:36-136`,
`tests/test_routing.py:54-160`, and
`tests/test_evals.py:37-74`.

---

## Guide Selection

| If You Are Changing | Read First | Then Check |
|---------------------|------------|------------|
| Module placement or package layout | Directory Structure | Quality Guidelines |
| CLI parser or dispatch behavior | Directory Structure | Error Handling |
| Workspace directories or JSON files | State Persistence | Quality Guidelines |
| Missing files, invalid drafts, bad source names, or CLI errors | Error Handling | State Persistence |
| stdout, stderr, or diagnostic behavior | Logging Guidelines | Error Handling |
| Routing scores, reasons, or evidence | Quality Guidelines | State Persistence |
| Source cloning, updating, or scanning | State Persistence | Quality Guidelines |
| Draft proposal, approval, or export | State Persistence | Error Handling |
| Tests | Quality Guidelines | The guide for the feature area |

---

## Scope Boundaries

These backend guidelines apply to:

- `src/skill_manager/__init__.py`
- `src/skill_manager/models.py`
- `src/skill_manager/workspace.py`
- `src/skill_manager/text.py`
- `src/skill_manager/frontmatter.py`
- `src/skill_manager/sources.py`
- `src/skill_manager/routing.py`
- `src/skill_manager/derive.py`
- `src/skill_manager/project.py`
- `src/skill_manager/export.py`
- `src/skill_manager/evals.py`
- `tests/test_*.py`

These backend guidelines do not define frontend structure, HTTP handlers,
database migrations, ORM models, background workers, or deployment topology.
Those concepts do not exist in the current implementation.

---

## How To Keep This Directory Current

1. Update the relevant guide in the same change that alters a backend
   convention.
2. Cite source or test lines for every new guideline.
3. Prefer documenting current behavior over aspirational patterns.
4. If a guide name no longer matches the implementation, rename or supersede it
   in this index.
5. Keep generated documentation in English.

---

## Current Backend Shape

The backend is a Python 3.12+ package with console scripts wired to
`skill_manager:main`. The entrypoint exposes `skill-manager` and `skillmgr`,
then delegates subcommands to focused modules through lazy imports
(`pyproject.toml:9-14`, `src/skill_manager/__init__.py:74-121`).

The state model is workspace-centric. `Workspace` derives the root from
`SKILL_MANAGER_HOME` or `~/.skill-manager`, defines seven state directories,
and ensures those directories before feature modules read or write state
(`src/skill_manager/workspace.py:9-33`).

The runtime dependency model is intentionally small. Frontmatter parsing,
routing text matching, git subprocess handling, and JSON persistence use the
standard library (`src/skill_manager/frontmatter.py:3-9`,
`src/skill_manager/text.py:3-7`, `src/skill_manager/sources.py:3-11`,
`src/skill_manager/workspace.py:3-6`).

Tests are flat and isolate filesystem state with `tmp_path`. They cover source
subscription, scanning, routing, derivation, export, project draft generation,
frontmatter parsing, CLI parsing, and eval metrics (`tests/test_sources.py:36-136`,
`tests/test_routing.py:54-160`, `tests/test_derive_export.py:37-142`,
`tests/test_frontmatter.py:6-17`, `tests/test_cli.py:4-9`,
`tests/test_evals.py:37-74`).

---

**Language**: All documentation should be written in **English**.
