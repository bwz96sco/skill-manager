# Skill Manager

Local-first manager for subscribing to `SKILL.md` repositories, deriving
provenance-backed meta-skills, and routing natural-language tasks to relevant
skills without taking over execution.

## V1 Goal

`skill-manager` is an advisory layer:

- subscribe to GitHub or local git skill repositories;
- keep upstream sources read-only and update them with `git pull`;
- scan `SKILL.md` metadata and evidence snippets;
- derive meta-skill drafts with common logic separated from source-specific variants;
- generate project-specific skill drafts;
- route user tasks to top-k skill candidates with evidence and confidence;
- export only approved generated entries to host skill directories.

## CLI

```bash
uv run skillmgr source add aris /path/to/Auto-claude-code-research-in-sleep --path skills/skills-codex
uv run skillmgr scan
uv run skillmgr derive propose
uv run skillmgr route "需要GPU算力跑实验"
uv run skillmgr eval run
```

The default workspace is `~/.skill-manager`; pass `--workspace <path>` to keep
all sources, registries, indexes, drafts, and exports under a test directory.

## Verification Standard

V1 is not complete unless:

- subscribed sources record URL, commit, skill path, and parsed skill metadata;
- updates report changed source commits and affected derived content;
- golden routing evals improve recall over keyword-only matching for mixed
  English/Chinese prompts;
- every generated meta-skill rule links to source evidence;
- common logic and source-specific variants are separated;
- raw external skills are not exported unless explicitly requested.
