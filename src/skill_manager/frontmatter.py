from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_PAIR_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")


def decode_scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value.replace("'", '"'))
        except json.JSONDecodeError:
            return value
    return value


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        return {}, text

    metadata: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] = []
    for line in lines[1:end]:
        if line.strip().startswith("- ") and current_key:
            current_list.append(str(decode_scalar(line.strip()[2:])))
            metadata[current_key] = current_list
            continue
        match = _PAIR_RE.match(line)
        if not match:
            current_key = None
            current_list = []
            continue
        key, raw_value = match.groups()
        value = decode_scalar(raw_value)
        if value == "":
            current_key = key
            current_list = []
            metadata[key] = current_list
        else:
            current_key = None
            current_list = []
            metadata[key] = value
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return metadata, body
