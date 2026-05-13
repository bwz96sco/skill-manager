from __future__ import annotations

import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .frontmatter import parse_frontmatter
from .models import Evidence, SkillRecord, SourceRecord, to_jsonable
from .text import digest
from .workspace import Workspace, read_json, write_json


def add_source(
    name: str,
    url: str,
    skill_root: str,
    ref: str = "main",
    workspace: str | Path | Workspace | None = None,
) -> SourceRecord:
    ws = _workspace(workspace)
    records = _load_sources(ws)
    destination = _source_dir(ws, name)
    existing = records.get(name)
    if existing:
        if existing.url == url and existing.skill_root == skill_root and existing.ref == ref and destination.exists():
            return existing
        raise ValueError(f"source already exists with different configuration: {name}")

    if not destination.exists():
        try:
            _git(["clone", "--branch", ref, url, str(destination)])
        except subprocess.CalledProcessError:
            _git(["clone", url, str(destination)])
            _git(["checkout", ref], cwd=destination)
    commit = _commit(destination)
    record = SourceRecord(name=name, url=url, skill_root=skill_root, ref=ref, commit=commit)
    records[name] = record
    _write_sources(ws, records)
    return record


def update_sources(
    name: str | None = None,
    workspace: str | Path | Workspace | None = None,
) -> list[str]:
    ws = _workspace(workspace)
    records = _load_sources(ws)
    selected_names = [name] if name else sorted(records)
    changed: list[str] = []
    for selected in selected_names:
        if selected not in records:
            raise KeyError(selected)
        checkout = _source_dir(ws, selected)
        before = records[selected].commit or _commit(checkout)
        _git(["pull", "--ff-only"], cwd=checkout)
        after = _commit(checkout)
        records[selected].commit = after
        if before != after:
            changed.append(selected)
            changed_skill_ids = _source_skill_ids(ws, selected)
            _append_update_log(
                ws,
                {
                    "source": selected,
                    "before": before,
                    "after": after,
                    "changed_skill_ids": changed_skill_ids,
                    "affected_drafts": _affected_drafts(ws, changed_skill_ids),
                },
            )
    _write_sources(ws, records)
    return changed


def scan_sources(workspace: str | Path | Workspace | None = None) -> list[SkillRecord]:
    ws = _workspace(workspace)
    records = _load_sources(ws)
    skills: list[SkillRecord] = []
    for source in records.values():
        checkout = _source_dir(ws, source.name)
        root = checkout / source.skill_root
        if not root.exists():
            continue
        for skill_path in sorted(root.rglob("SKILL.md")):
            metadata, body = parse_frontmatter(skill_path)
            full_text = skill_path.read_text(encoding="utf-8-sig")
            skill_id = str(metadata.get("name") or skill_path.parent.name).strip()
            relative = str(skill_path.relative_to(checkout))
            evidence = _evidence_for_body(
                source=source,
                skill_id=skill_id,
                relative_path=relative,
                full_text=full_text,
                body=body,
            )
            description = str(metadata.get("description") or "")
            skills.append(
                SkillRecord(
                    skill_id=skill_id,
                    name=skill_id,
                    description=description,
                    source=source.name,
                    source_url=source.url,
                    source_commit=source.commit,
                    path=relative,
                    digest=digest(full_text),
                    tags=_tags(metadata.get("tags")),
                    free_tags=_dedupe(
                        [
                            *_list(metadata.get("free_tags")),
                            *_inferred_free_tags(skill_id, description, body),
                        ]
                    ),
                    aliases=_dedupe(
                        [
                            *_list(metadata.get("aliases")),
                            *_inferred_aliases(skill_id, description),
                        ]
                    ),
                    evidence=[evidence] if evidence else [],
                )
            )
    write_json(ws.registry / "skills.json", [to_jsonable(skill) for skill in skills])
    return skills


def _workspace(workspace: str | Path | Workspace | None) -> Workspace:
    ws = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    ws.ensure()
    return ws


def _source_dir(workspace: Workspace, name: str) -> Path:
    return workspace.sources / name


def _load_sources(workspace: Workspace) -> dict[str, SourceRecord]:
    payload = read_json(workspace.registry / "sources.json", [])
    rows: list[dict[str, Any]]
    if isinstance(payload, dict):
        rows = list(payload.get("sources", []))
    else:
        rows = list(payload)
    records: dict[str, SourceRecord] = {}
    for row in rows:
        if isinstance(row, dict):
            record = SourceRecord(
                name=str(row.get("name", "")),
                url=str(row.get("url", "")),
                skill_root=str(row.get("skill_root", ".")),
                ref=str(row.get("ref", "main")),
                commit=str(row.get("commit", "")),
            )
            if record.name:
                records[record.name] = record
    return records


def _write_sources(workspace: Workspace, records: dict[str, SourceRecord]) -> None:
    write_json(workspace.registry / "sources.json", [asdict(records[name]) for name in sorted(records)])


def _source_skill_ids(workspace: Workspace, source_name: str) -> list[str]:
    payload = read_json(workspace.registry / "skills.json", [])
    raw_skills = payload.get("skills", []) if isinstance(payload, dict) else payload
    if not isinstance(raw_skills, list):
        return []
    ids: list[str] = []
    for item in raw_skills:
        if isinstance(item, dict) and item.get("source") == source_name and item.get("skill_id"):
            ids.append(str(item["skill_id"]))
    return sorted(set(ids))


def _affected_drafts(workspace: Workspace, changed_skill_ids: list[str]) -> list[str]:
    changed = set(changed_skill_ids)
    if not changed:
        return []
    affected: list[str] = []
    for path in sorted(workspace.derived.glob("*.json")):
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            continue
        source_skill_ids = payload.get("source_skill_ids", [])
        if not isinstance(source_skill_ids, list):
            continue
        if changed & {str(item) for item in source_skill_ids}:
            affected.append(str(payload.get("draft_id") or path.stem))
    return affected


def _append_update_log(workspace: Workspace, entry: dict[str, Any]) -> None:
    path = workspace.registry / "update-log.json"
    payload = read_json(path, [])
    entries = payload if isinstance(payload, list) else []
    entries.append(entry)
    write_json(path, entries)


def _git(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _commit(path: Path) -> str:
    return _git(["rev-parse", "HEAD"], cwd=path)


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


def _inferred_free_tags(skill_id: str, description: str, body: str) -> list[str]:
    identity_text = f"{skill_id}\n{description}".casefold()
    tags: list[str] = []
    has_gpu = "gpu" in identity_text
    rental_gpu = any(term in identity_text for term in ("vast-gpu", "vast.ai", "vastai")) or (
        has_gpu and any(term in identity_text for term in ("rent", "cloud", "serverless", "modal", "gpu instances"))
    )
    if rental_gpu:
        tags.extend(
            [
                "GPU算力",
                "GPU服务器",
                "云GPU",
                "云算力",
                "租GPU",
                "租用GPU",
                "显卡服务器",
                "算力租用",
                "跑实验",
                "训练模型",
            ]
        )
    elif has_gpu:
        tags.extend(["GPU", "显卡"])
    if any(term in identity_text for term in ("citation", "cite", "bibliograph", "reference")):
        tags.extend(["审查引用", "引用核对", "检查引用", "参考文献", "论文引用", "citation audit"])
    return tags


def _inferred_aliases(skill_id: str, description: str) -> list[str]:
    haystack = f"{skill_id}\n{description}".casefold()
    aliases: list[str] = []
    if "vast-gpu" in haystack or "vast.ai" in haystack or "vastai" in haystack:
        aliases.extend(["gpu rent", "rent gpu", "vast", "vast.ai"])
    elif "gpu" in haystack and ("serverless" in haystack or "modal" in haystack or "cloud" in haystack):
        aliases.extend(["cloud gpu", "serverless gpu"])
    if any(term in haystack for term in ("citation", "cite", "bibliograph", "reference")):
        aliases.extend(["审查引用", "引用核对", "check citations", "verify references"])
    return aliases


def _tags(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    return {str(key): _list(items) for key, items in value.items()}


def _evidence_for_body(
    source: SourceRecord,
    skill_id: str,
    relative_path: str,
    full_text: str,
    body: str,
) -> Evidence | None:
    chunk = _first_nonempty_block(body)
    if not chunk:
        return None
    lines = full_text.splitlines()
    chunk_first = chunk.splitlines()[0].strip()
    start = next((index for index, line in enumerate(lines, start=1) if line.strip() == chunk_first), 1)
    end = start + len(chunk.splitlines()) - 1
    return Evidence(
        source=source.name,
        skill_id=skill_id,
        path=relative_path,
        commit=source.commit,
        line_start=start,
        line_end=end,
        chunk_hash=digest(chunk),
        text=chunk,
    )


def _first_nonempty_block(body: str) -> str:
    current: list[str] = []
    for line in body.splitlines():
        if line.strip():
            current.append(line.rstrip())
            continue
        if current:
            break
    return "\n".join(current).strip()
