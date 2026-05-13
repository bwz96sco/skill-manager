from __future__ import annotations

import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from .models import Evidence, MetaSkillDraft, to_jsonable
from .text import digest, tokens
from .workspace import Workspace, read_json, write_json


_STOPWORDS = {
    "a",
    "an",
    "and",
    "assistant",
    "code",
    "codex",
    "for",
    "guide",
    "in",
    "of",
    "on",
    "skill",
    "the",
    "to",
    "use",
    "when",
    "with",
}


def _workspace(workspace: str | Path | Workspace | None) -> Workspace:
    if isinstance(workspace, Workspace):
        ws = workspace
    else:
        ws = Workspace(workspace)
    ws.ensure()
    return ws


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "skill"


def _skills(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        raw = payload.get("skills", payload)
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, dict):
            return [item for item in raw.values() if isinstance(item, dict)]
    return []


def _values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def _cluster_keys(skill: dict[str, Any]) -> list[str]:
    tags = skill.get("tags") if isinstance(skill.get("tags"), dict) else {}
    keys = [f"task:{_slug(item)}" for item in _values(tags.get("task"))]
    keys.extend(f"domain:{_slug(item)}" for item in _values(tags.get("domain")))
    if keys:
        return keys

    for token in _identity_parts(skill):
        if len(token) > 2 and token not in _STOPWORDS:
            return [f"name:{_slug(token)}"]
    return [f"name:{_slug(skill.get('skill_id') or skill.get('name') or 'skill')}"]


def _identity_parts(skill: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for field in ("name", "skill_id"):
        value = str(skill.get(field) or "")
        for token in tokens(value):
            parts.extend(part for part in re.split(r"[^a-z0-9]+", token.casefold()) if part)
    return parts


def _evidence(skill: dict[str, Any]) -> list[Evidence]:
    evidence = skill.get("evidence")
    if isinstance(evidence, list) and evidence:
        out: list[Evidence] = []
        for item in evidence:
            if isinstance(item, Evidence):
                out.append(item)
            elif isinstance(item, dict):
                out.append(
                    Evidence(
                        source=str(item.get("source", skill.get("source", ""))),
                        skill_id=str(item.get("skill_id", skill.get("skill_id", ""))),
                        path=str(item.get("path", skill.get("path", ""))),
                        commit=str(item.get("commit", skill.get("source_commit", ""))),
                        line_start=int(item.get("line_start", 1) or 1),
                        line_end=int(item.get("line_end", item.get("line_start", 1)) or 1),
                        chunk_hash=str(item.get("chunk_hash", "")),
                        text=str(item.get("text", "")),
                    )
                )
        return out

    text = str(skill.get("description") or skill.get("name") or "")
    return [
        Evidence(
            source=str(skill.get("source", "")),
            skill_id=str(skill.get("skill_id", "")),
            path=str(skill.get("path", "")),
            commit=str(skill.get("source_commit", "")),
            line_start=1,
            line_end=1,
            chunk_hash=digest(text)[:16],
            text=text,
        )
    ]


def _logic_for(skill: dict[str, Any]) -> str:
    description = str(skill.get("description") or "").strip()
    name = str(skill.get("name") or skill.get("skill_id") or "skill").strip()
    return description or f"Apply the workflow from {name}."


def _variant_for(skill: dict[str, Any]) -> str:
    name = str(skill.get("name") or skill.get("skill_id") or "skill")
    source = str(skill.get("source") or "unknown source")
    path = str(skill.get("path") or "unknown path")
    return f"{name} ({source}): keep source-specific behavior from {path}."


def _title(cluster_key: str) -> str:
    _, _, value = cluster_key.partition(":")
    words = value.replace("-", " ").strip()
    return f"{words.title()} Meta Skill" if words else "Meta Skill"


def _draft_from_cluster(cluster_key: str, grouped: list[dict[str, Any]]) -> MetaSkillDraft:
    skills = sorted(grouped, key=lambda item: str(item.get("skill_id") or item.get("name") or ""))
    skill_ids = [str(item.get("skill_id") or item.get("name") or "") for item in skills]
    draft_seed = "|".join([cluster_key, *skill_ids])
    draft_id = f"meta-{_slug(cluster_key)}-{digest(draft_seed)[:8]}"

    common_logic = []
    seen_logic: set[str] = set()
    for skill in skills:
        logic = _logic_for(skill)
        if logic not in seen_logic:
            common_logic.append(logic)
            seen_logic.add(logic)

    evidence: list[Evidence] = []
    for skill in skills:
        evidence.extend(_evidence(skill))

    return MetaSkillDraft(
        draft_id=draft_id,
        title=_title(cluster_key),
        cluster_key=cluster_key,
        common_logic=common_logic,
        variants=[_variant_for(skill) for skill in skills],
        source_skill_ids=skill_ids,
        evidence=evidence,
        approved=False,
    )


def _markdown(draft: MetaSkillDraft) -> str:
    lines = [
        f"# {draft.title}",
        "",
        "## Common Logic",
        "",
        *[f"- {item}" for item in draft.common_logic],
        "",
        "## Source-Specific Variants",
        "",
        *[f"- {item}" for item in draft.variants],
        "",
        "## Provenance",
        "",
    ]
    for item in draft.evidence:
        location = item.path
        if item.line_start or item.line_end:
            location = f"{location}:{item.line_start}-{item.line_end}"
        lines.append(f"- {item.source}/{item.skill_id} ({item.commit}) {location}")
    return "\n".join(lines).rstrip() + "\n"


def _summary(draft: MetaSkillDraft, json_path: Path, markdown_path: Path) -> dict[str, Any]:
    return {
        "draft_id": draft.draft_id,
        "title": draft.title,
        "cluster_key": draft.cluster_key,
        "source_skill_ids": list(draft.source_skill_ids),
        "approved": draft.approved,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }


def propose(workspace: str | Path | Workspace | None = None) -> list[dict[str, Any]]:
    ws = _workspace(workspace)
    skills = _skills(read_json(ws.registry / "skills.json", []))

    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    assigned: set[str] = set()
    for skill in sorted(skills, key=lambda item: str(item.get("skill_id") or item.get("name") or "")):
        skill_key = str(skill.get("skill_id") or skill.get("name") or id(skill))
        for key in _cluster_keys(skill):
            clusters[key].append(skill)
            assigned.add(skill_key)
            break

    summaries: list[dict[str, Any]] = []
    for key in sorted(clusters):
        grouped = clusters[key]
        if len(grouped) < 2:
            continue
        draft = _draft_from_cluster(key, grouped)
        json_path = ws.drafts / f"{draft.draft_id}.json"
        markdown_path = ws.drafts / f"{draft.draft_id}.md"
        write_json(json_path, to_jsonable(draft))
        markdown_path.write_text(_markdown(draft), encoding="utf-8")
        summaries.append(_summary(draft, json_path, markdown_path))

    if not summaries and skills:
        draft = _draft_from_cluster("name:all-skills", skills)
        json_path = ws.drafts / f"{draft.draft_id}.json"
        markdown_path = ws.drafts / f"{draft.draft_id}.md"
        write_json(json_path, to_jsonable(draft))
        markdown_path.write_text(_markdown(draft), encoding="utf-8")
        summaries.append(_summary(draft, json_path, markdown_path))

    return summaries


def approve(draft_id: str, workspace: str | Path | Workspace | None = None) -> dict[str, Any]:
    ws = _workspace(workspace)
    json_path = ws.drafts / f"{draft_id}.json"
    markdown_path = ws.drafts / f"{draft_id}.md"
    if not json_path.exists() or not markdown_path.exists():
        raise FileNotFoundError(f"Draft {draft_id!r} is missing from {ws.drafts}")

    payload = read_json(json_path, {})
    if not isinstance(payload, dict):
        raise ValueError(f"Draft {draft_id!r} JSON is not an object")
    payload["approved"] = True
    payload["generated_by"] = payload.get("generated_by", "derive.propose")
    write_json(json_path, payload)

    derived_json = ws.derived / f"{draft_id}.json"
    derived_markdown = ws.derived / f"{draft_id}.md"
    write_json(derived_json, payload)
    derived_markdown.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(markdown_path, derived_markdown)

    return {
        "draft_id": draft_id,
        "approved": True,
        "json_path": str(derived_json),
        "markdown_path": str(derived_markdown),
        "status": "approved",
    }
