from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .text import digest
from .workspace import Workspace, write_json


_PROJECT_FILES = ("README.md", "AGENTS.md", "CLAUDE.md")


def _workspace(workspace: str | Path | Workspace | None) -> Workspace:
    if isinstance(workspace, Workspace):
        ws = workspace
    else:
        ws = Workspace(workspace)
    ws.ensure()
    return ws


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "project"


def _excerpt(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines[:3])[:280] or "No project guidance text found."


def _markdown(title: str, read_files: list[dict[str, Any]]) -> str:
    common = [
        "Apply the project-local instructions before general skill guidance.",
        "Prefer commands, tools, and conventions explicitly named by the project.",
        "Treat these files as provenance for generated workflow advice.",
    ]
    lines = [
        f"# {title}",
        "",
        "## Common Logic",
        "",
        *[f"- {item}" for item in common],
        "",
        "## Source-Specific Variants",
        "",
    ]
    for item in read_files:
        lines.append(f"- {item['name']}: {_excerpt(str(item['text']))}")
    lines.extend(["", "## Provenance", ""])
    for item in read_files:
        lines.append(f"- {item['path']}")
    return "\n".join(lines).rstrip() + "\n"


def propose(project_path: str | Path, workspace: str | Path | Workspace | None = None) -> dict[str, Any]:
    ws = _workspace(workspace)
    project_root = Path(project_path).expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise FileNotFoundError(f"Project path {project_root} does not exist or is not a directory")

    read_files: list[dict[str, Any]] = []
    for name in _PROJECT_FILES:
        path = project_root / name
        if path.exists() and path.is_file():
            read_files.append(
                {
                    "name": name,
                    "path": str(path),
                    "text": path.read_text(encoding="utf-8"),
                }
            )

    if not read_files:
        raise FileNotFoundError(f"No project guidance files found in {project_root}")

    seed = "|".join([str(project_root), *[item["path"] + ":" + digest(str(item["text"])) for item in read_files]])
    draft_id = f"project-{_slug(project_root.name)}-{digest(seed)[:8]}"
    title = f"{project_root.name} Project Skill"
    payload: dict[str, Any] = {
        "draft_id": draft_id,
        "title": title,
        "cluster_key": f"project:{_slug(project_root.name)}",
        "common_logic": [
            "Apply the project-local instructions before general skill guidance.",
            "Prefer commands, tools, and conventions explicitly named by the project.",
            "Treat these files as provenance for generated workflow advice.",
        ],
        "variants": [f"{item['name']}: {_excerpt(str(item['text']))}" for item in read_files],
        "source_skill_ids": [],
        "evidence": [
            {
                "source": "project",
                "skill_id": draft_id,
                "path": item["path"],
                "commit": "",
                "line_start": 1,
                "line_end": len(str(item["text"]).splitlines()) or 1,
                "chunk_hash": digest(str(item["text"]))[:16],
                "text": _excerpt(str(item["text"])),
            }
            for item in read_files
        ],
        "approved": False,
        "generated_by": "project.propose",
        "project_path": str(project_root),
        "provenance": [item["path"] for item in read_files],
    }

    json_path = ws.drafts / f"{draft_id}.json"
    markdown_path = ws.drafts / f"{draft_id}.md"
    write_json(json_path, payload)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_markdown(title, read_files), encoding="utf-8")

    return {
        "draft_id": draft_id,
        "title": title,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "provenance": [item["path"] for item in read_files],
        "approved": False,
    }
