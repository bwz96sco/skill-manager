from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from skill_manager.routing import route
from skill_manager.sources import add_source, scan_sources, update_sources
from skill_manager.workspace import read_json, write_json


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _make_repo(path: Path, skill_name: str = "demo-skill") -> Path:
    path.mkdir(parents=True)
    _git(path, "init")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test User")
    skill_dir = path / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f'---\nname: {skill_name}\ndescription: "Use when serverless: modal is needed"\n'
        "aliases:\n- demo alias\n---\n# Demo Skill\n\nUse this skill for tests.\n",
        encoding="utf-8",
    )
    _git(path, "add", ".")
    _git(path, "commit", "-m", "initial")
    _git(path, "branch", "-M", "main")
    return path


def test_add_source_clones_and_records_registry(tmp_path: Path) -> None:
    upstream = _make_repo(tmp_path / "upstream")
    workspace = tmp_path / "workspace"

    record = add_source("demo", str(upstream), "skills", workspace=workspace)

    assert record.name == "demo"
    assert (workspace / "sources" / "demo" / "skills" / "demo-skill" / "SKILL.md").is_file()
    registry = json.loads((workspace / "registry" / "sources.json").read_text(encoding="utf-8"))
    assert registry[0]["commit"] == _git(upstream, "rev-parse", "HEAD")


def test_scan_sources_writes_skills_json_and_leaves_checkout_clean(tmp_path: Path) -> None:
    upstream = _make_repo(tmp_path / "upstream")
    workspace = tmp_path / "workspace"
    add_source("demo", str(upstream), "skills", workspace=workspace)

    skills = scan_sources(workspace)

    assert [skill.skill_id for skill in skills] == ["demo-skill"]
    skill = skills[0]
    assert skill.description == "Use when serverless: modal is needed"
    assert skill.aliases == ["demo alias"]
    assert skill.evidence[0].path == "skills/demo-skill/SKILL.md"
    assert skill.evidence[0].line_start > 0
    assert "Demo Skill" in skill.evidence[0].text
    written = json.loads((workspace / "registry" / "skills.json").read_text(encoding="utf-8"))
    assert written[0]["evidence"][0]["chunk_hash"]
    assert _git(workspace / "sources" / "demo", "status", "--short") == ""


def test_update_sources_reports_changed_commit(tmp_path: Path) -> None:
    upstream = _make_repo(tmp_path / "upstream")
    workspace = tmp_path / "workspace"
    add_source("demo", str(upstream), "skills", workspace=workspace)
    scan_sources(workspace)
    write_json(
        workspace / "derived" / "meta-demo.json",
        {"draft_id": "meta-demo", "approved": True, "source_skill_ids": ["demo-skill"]},
    )
    skill_file = upstream / "skills" / "demo-skill" / "SKILL.md"
    skill_file.write_text(skill_file.read_text(encoding="utf-8") + "\nMore guidance.\n", encoding="utf-8")
    _git(upstream, "add", ".")
    _git(upstream, "commit", "-m", "update skill")

    changed = update_sources(workspace=workspace)

    assert changed == ["demo"]
    log = read_json(workspace / "registry" / "update-log.json", [])
    assert log[-1]["changed_skill_ids"] == ["demo-skill"]
    assert log[-1]["affected_drafts"] == ["meta-demo"]


def test_file_url_source_and_unknown_update(tmp_path: Path) -> None:
    upstream = _make_repo(tmp_path / "upstream")
    workspace = tmp_path / "workspace"

    record = add_source("demo", upstream.as_uri(), "skills", workspace=workspace)

    assert record.commit
    with pytest.raises(KeyError):
        update_sources("missing", workspace=workspace)


def test_scan_infers_cross_language_tags_for_gpu_skill(tmp_path: Path) -> None:
    upstream = _make_repo(tmp_path / "upstream", "vast-gpu")
    skill_file = upstream / "skills" / "vast-gpu" / "SKILL.md"
    skill_file.write_text(
        '---\nname: vast-gpu\n'
        'description: "Rent, manage, and destroy GPU instances on vast.ai for on-demand training."\n'
        "---\n# Vast GPU\n\nRent a cloud GPU for machine learning experiments.\n",
        encoding="utf-8",
    )
    _git(upstream, "add", ".")
    _git(upstream, "commit", "-m", "gpu skill")
    workspace = tmp_path / "workspace"
    add_source("demo", str(upstream), "skills", workspace=workspace)

    skills = scan_sources(workspace)

    assert "GPU算力" in skills[0].free_tags
    assert route("需要GPU算力跑实验", workspace)[0].skill_id == "vast-gpu"


def test_scan_does_not_infer_gpu_tags_from_incidental_body_mentions(tmp_path: Path) -> None:
    upstream = _make_repo(tmp_path / "upstream", "experiment-plan")
    skill_file = upstream / "skills" / "experiment-plan" / "SKILL.md"
    skill_file.write_text(
        '---\nname: experiment-plan\n'
        'description: "Plan machine learning experiments and ablations."\n'
        "---\n# Experiment Plan\n\nMay mention GPU budgets as one possible resource.\n",
        encoding="utf-8",
    )
    _git(upstream, "add", ".")
    _git(upstream, "commit", "-m", "experiment skill")
    workspace = tmp_path / "workspace"
    add_source("demo", str(upstream), "skills", workspace=workspace)

    skills = scan_sources(workspace)

    assert "GPU算力" not in skills[0].free_tags
