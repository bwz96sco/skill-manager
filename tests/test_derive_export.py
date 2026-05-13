from __future__ import annotations

from pathlib import Path

import pytest

from skill_manager import derive, export, project
from skill_manager.workspace import read_json, write_json


def _skill(skill_id: str, name: str, task: str, domain: str, source: str) -> dict[str, object]:
    return {
        "skill_id": skill_id,
        "name": name,
        "description": f"Use {name} for repeatable {task} work.",
        "source": source,
        "source_url": f"https://example.test/{source}",
        "source_commit": "abc123",
        "path": f"{skill_id}/SKILL.md",
        "digest": skill_id,
        "tags": {"task": [task], "domain": [domain]},
        "evidence": [
            {
                "source": source,
                "skill_id": skill_id,
                "path": f"{skill_id}/SKILL.md",
                "commit": "abc123",
                "line_start": 1,
                "line_end": 8,
                "chunk_hash": skill_id,
                "text": f"{name} evidence",
            }
        ],
    }


def test_derive_propose_approve_and_export(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_json(
        workspace / "registry" / "skills.json",
        {
            "skills": [
                _skill("lit-a", "Literature Search", "research", "papers", "alpha"),
                _skill("lit-b", "Research Review", "research", "papers", "beta"),
                _skill("deploy", "Deploy Helper", "deploy", "ops", "gamma"),
            ]
        },
    )

    drafts = derive.propose(workspace)

    assert len(drafts) == 1
    draft_id = drafts[0]["draft_id"]
    markdown = (workspace / "drafts" / f"{draft_id}.md").read_text(encoding="utf-8")
    assert "## Common Logic" in markdown
    assert "## Source-Specific Variants" in markdown
    assert "## Provenance" in markdown
    assert "alpha/lit-a" in markdown
    assert "beta/lit-b" in markdown

    approved = derive.approve(draft_id, workspace)

    assert approved["status"] == "approved"
    assert read_json(workspace / "derived" / f"{draft_id}.json", {})["approved"] is True

    dest = tmp_path / "exports"
    exported = export.apply(draft_id, "project", workspace, dest)

    installed = dest / draft_id / "SKILL.md"
    assert exported["path"] == str(installed)
    assert installed.read_text(encoding="utf-8") == (workspace / "derived" / f"{draft_id}.md").read_text(
        encoding="utf-8"
    )


def test_project_propose_records_project_file_provenance(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Demo\nUse uv for Python tasks.\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("Always use Context7 for API docs.\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text("Follow project conventions.\n", encoding="utf-8")

    draft = project.propose(repo, workspace)

    assert draft["approved"] is False
    assert set(draft["provenance"]) == {
        str(repo / "README.md"),
        str(repo / "AGENTS.md"),
        str(repo / "CLAUDE.md"),
    }
    markdown = Path(draft["markdown_path"]).read_text(encoding="utf-8")
    assert "## Provenance" in markdown
    assert str(repo / "AGENTS.md") in markdown


def test_export_rejects_unapproved_missing_and_raw(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    dest = tmp_path / "exports"

    write_json(
        workspace / "derived" / "meta-unapproved.json",
        {"draft_id": "meta-unapproved", "approved": False, "generated_by": "derive.propose"},
    )
    (workspace / "derived" / "meta-unapproved.md").parent.mkdir(parents=True, exist_ok=True)
    (workspace / "derived" / "meta-unapproved.md").write_text("# Unapproved\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not approved"):
        export.apply("meta-unapproved", "project", workspace, dest)

    with pytest.raises(FileNotFoundError):
        export.apply("missing", "project", workspace, dest)

    write_json(
        workspace / "derived" / "raw-source.json",
        {"draft_id": "raw-source", "approved": True, "generated_by": "source.scan"},
    )
    (workspace / "derived" / "raw-source.md").write_text("# Raw Source\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not a generated"):
        export.apply("raw-source", "project", workspace, dest)

    with pytest.raises(ValueError, match="requires explicit dest"):
        export.apply("raw-source", "project", workspace)


def test_derive_clusters_hyphenated_skill_ids_without_tags(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_json(
        workspace / "registry" / "skills.json",
        [
            _skill("paper-write", "paper-write", "", "", "alpha"),
            _skill("paper-compile", "paper-compile", "", "", "alpha"),
            _skill("gpu-rent", "gpu-rent", "", "", "beta"),
        ],
    )

    drafts = derive.propose(workspace)

    paper_drafts = [draft for draft in drafts if draft["cluster_key"] == "name:paper"]
    assert len(paper_drafts) == 1
    assert paper_drafts[0]["source_skill_ids"] == ["paper-compile", "paper-write"]
