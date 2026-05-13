from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .workspace import Workspace, read_json


_DEFAULT_DESTS = {
    "agents": Path("~/.agents/skills").expanduser(),
    "claude": Path("~/.claude/skills").expanduser(),
    "codex": Path("~/.codex/skills").expanduser(),
}

_GENERATORS = {"derive.propose", "project.propose"}


def _workspace(workspace: str | Path | Workspace | None) -> Workspace:
    if isinstance(workspace, Workspace):
        ws = workspace
    else:
        ws = Workspace(workspace)
    ws.ensure()
    return ws


def _destination(target: str, dest: str | Path | None) -> Path:
    if target == "project":
        if dest is None:
            raise ValueError("target 'project' requires explicit dest")
        return Path(dest).expanduser()
    if target not in _DEFAULT_DESTS:
        raise ValueError(f"Unknown export target {target!r}")
    return Path(dest).expanduser() if dest is not None else _DEFAULT_DESTS[target]


def _is_generated(payload: dict[str, Any]) -> bool:
    generator = payload.get("generated_by")
    if generator in _GENERATORS:
        return True
    draft_id = str(payload.get("draft_id", ""))
    return draft_id.startswith("meta-") or draft_id.startswith("project-")


def apply(
    draft_id: str,
    target: str,
    workspace: str | Path | Workspace | None = None,
    dest: str | Path | None = None,
) -> dict[str, Any]:
    ws = _workspace(workspace)
    root = _destination(target, dest)
    json_path = ws.derived / f"{draft_id}.json"
    markdown_path = ws.derived / f"{draft_id}.md"
    if not json_path.exists() or not markdown_path.exists():
        raise FileNotFoundError(f"Approved generated draft {draft_id!r} is missing from {ws.derived}")

    payload = read_json(json_path, {})
    if not isinstance(payload, dict):
        raise ValueError(f"Approved draft {draft_id!r} JSON is not an object")
    if payload.get("approved") is not True:
        raise ValueError(f"Draft {draft_id!r} is not approved")
    if not _is_generated(payload):
        raise ValueError(f"Draft {draft_id!r} is not a generated meta/project skill")

    install_dir = root / draft_id
    install_dir.mkdir(parents=True, exist_ok=True)
    installed = install_dir / "SKILL.md"
    shutil.copyfile(markdown_path, installed)

    return {
        "draft_id": draft_id,
        "target": target,
        "path": str(installed),
        "status": "exported",
    }
