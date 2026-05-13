from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_WORKSPACE = Path(os.environ.get("SKILL_MANAGER_HOME", "~/.skill-manager")).expanduser()


class Workspace:
    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root).expanduser() if root else DEFAULT_WORKSPACE
        self.sources = self.root / "sources"
        self.registry = self.root / "registry"
        self.index = self.root / "index"
        self.derived = self.root / "derived"
        self.drafts = self.root / "drafts"
        self.exports = self.root / "exports"
        self.evals = self.root / "evals"

    def ensure(self) -> None:
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

    def path(self, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        return self.root / path


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
