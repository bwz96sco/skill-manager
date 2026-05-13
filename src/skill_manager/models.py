from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


CORE_TAGS = (
    "task",
    "domain",
    "stage",
    "tool",
    "risk",
    "input",
    "output",
    "host",
)


@dataclass
class SourceRecord:
    name: str
    url: str
    skill_root: str
    ref: str = "main"
    commit: str = ""


@dataclass
class Evidence:
    source: str
    skill_id: str
    path: str
    commit: str
    line_start: int
    line_end: int
    chunk_hash: str
    text: str


@dataclass
class SkillRecord:
    skill_id: str
    name: str
    description: str
    source: str
    source_url: str
    source_commit: str
    path: str
    digest: str
    tags: dict[str, list[str]] = field(default_factory=dict)
    free_tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class RouteCandidate:
    skill_id: str
    name: str
    source: str
    score: float
    reasons: list[str]
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class MetaSkillDraft:
    draft_id: str
    title: str
    cluster_key: str
    common_logic: list[str]
    variants: list[str]
    source_skill_ids: list[str]
    evidence: list[Evidence]
    approved: bool = False


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value
