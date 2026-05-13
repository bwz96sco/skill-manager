from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any, Iterable

from .models import Evidence, RouteCandidate, SkillRecord
from .text import cosine, keyword_hits, normalize, tokens
from .workspace import Workspace, read_json


def route(
    query: str,
    workspace: str | Path | Workspace | None = None,
    project: str | Path | None = None,
    top_k: int = 5,
) -> list[RouteCandidate]:
    ws = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    skills = _load_skills(ws)
    query_text = _query_text(query, project)
    query_norm = normalize(query_text)
    query_tokens = tokens(query_text)
    limit = max(0, top_k)

    candidates: list[RouteCandidate] = []
    for skill in skills:
        exact_reasons = _exact_reasons(query_norm, skill)
        if exact_reasons:
            candidates.append(
                RouteCandidate(
                    skill_id=skill.skill_id,
                    name=skill.name,
                    source=skill.source,
                    score=100.0 + len(exact_reasons),
                    reasons=exact_reasons,
                    evidence=skill.evidence,
                )
            )
            continue

        score, reasons = _lexical_score(query_text, query_tokens, skill)
        if score > 0:
            candidates.append(
                RouteCandidate(
                    skill_id=skill.skill_id,
                    name=skill.name,
                    source=skill.source,
                    score=score,
                    reasons=reasons,
                    evidence=skill.evidence,
                )
            )

    candidates.sort(key=lambda item: (-item.score, item.skill_id))
    return candidates[:limit]


def _query_text(query: str, project: str | Path | None) -> str:
    if project is None:
        return query
    return f"{query} {project}"


def _load_skills(workspace: Workspace) -> list[SkillRecord]:
    payload = read_json(workspace.registry / "skills.json", [])
    if isinstance(payload, dict):
        raw_skills = payload.get("skills") or payload.get("rows") or []
    else:
        raw_skills = payload
    if not isinstance(raw_skills, list):
        return []
    return [_skill_from_raw(item) for item in raw_skills if isinstance(item, dict)]


def _skill_from_raw(raw: dict[str, Any]) -> SkillRecord:
    values: dict[str, Any] = {}
    field_names = {field.name for field in fields(SkillRecord)}
    for name in field_names:
        if name in raw:
            values[name] = raw[name]
    values["evidence"] = [_evidence_from_raw(item) for item in raw.get("evidence", []) if isinstance(item, dict)]
    return SkillRecord(
        skill_id=str(values.get("skill_id", "")),
        name=str(values.get("name", "")),
        description=str(values.get("description", "")),
        source=str(values.get("source", "")),
        source_url=str(values.get("source_url", "")),
        source_commit=str(values.get("source_commit", "")),
        path=str(values.get("path", "")),
        digest=str(values.get("digest", "")),
        tags=_string_lists(values.get("tags", {})),
        free_tags=_string_list(values.get("free_tags", [])),
        aliases=_string_list(values.get("aliases", [])),
        evidence=values["evidence"],
    )


def _evidence_from_raw(raw: dict[str, Any]) -> Evidence:
    return Evidence(
        source=str(raw.get("source", "")),
        skill_id=str(raw.get("skill_id", "")),
        path=str(raw.get("path", "")),
        commit=str(raw.get("commit", "")),
        line_start=int(raw.get("line_start", 0) or 0),
        line_end=int(raw.get("line_end", 0) or 0),
        chunk_hash=str(raw.get("chunk_hash", "")),
        text=str(raw.get("text", "")),
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _string_lists(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    return {str(key): _string_list(items) for key, items in value.items()}


def _exact_reasons(query_norm: str, skill: SkillRecord) -> list[str]:
    reasons: list[str] = []
    for label, value in (
        ("skill_id", skill.skill_id),
        ("name", skill.name),
    ):
        if _substring_match(query_norm, value):
            reasons.append(f"exact {label} match: {value}")
    for alias in skill.aliases:
        if _substring_match(query_norm, alias):
            reasons.append(f"exact alias match: {alias}")
    return reasons


def _substring_match(query_norm: str, value: str) -> bool:
    value_norm = normalize(value)
    return bool(query_norm and value_norm and (value_norm in query_norm or query_norm in value_norm))


def _lexical_score(query_text: str, query_tokens: list[str], skill: SkillRecord) -> tuple[float, list[str]]:
    weighted_parts = _weighted_parts(skill)
    doc_tokens: list[str] = []
    score = 0.0
    reasons: list[str] = []

    for label, weight, values in weighted_parts:
        part_tokens = tokens(" ".join(values))
        doc_tokens.extend(part_tokens)
        similarity = cosine(query_tokens, part_tokens)
        if similarity > 0:
            score += weight * similarity
            reasons.append(f"{label} token similarity")

        direct_hits = keyword_hits(query_text, values)
        reverse_hits = _reverse_keyword_hits(query_tokens, values)
        hits = _dedupe([*direct_hits, *reverse_hits])
        if hits:
            score += weight * 0.35 * len(hits)
            reasons.append(f"{label} keyword hits: {', '.join(hits[:3])}")

    overall = cosine(query_tokens, doc_tokens)
    if overall > 0:
        score += overall
        reasons.append("overall token similarity")

    return score, _dedupe(reasons)


def _weighted_parts(skill: SkillRecord) -> list[tuple[str, float, list[str]]]:
    tag_values = _flatten_tags(skill.tags)
    return [
        ("identity", 4.0, [skill.skill_id, skill.name, *skill.aliases]),
        ("tags", 3.0, [*tag_values, *skill.free_tags]),
        ("description", 2.0, [skill.description]),
        ("evidence", 1.5, [item.text for item in skill.evidence]),
    ]


def _flatten_tags(tags: dict[str, list[str]]) -> list[str]:
    values: list[str] = []
    for items in tags.values():
        values.extend(items)
    return values


def _reverse_keyword_hits(query_tokens: Iterable[str], values: Iterable[str]) -> list[str]:
    hits: list[str] = []
    normalized_values = [(value, normalize(value)) for value in values]
    for token in query_tokens:
        token_norm = normalize(token)
        if not token_norm:
            continue
        for original, value_norm in normalized_values:
            if token_norm in value_norm:
                hits.append(str(original))
    return hits


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
