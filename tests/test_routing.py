from __future__ import annotations

import json
from pathlib import Path

from skill_manager.routing import route


def _write_registry(workspace: Path, skills: list[dict]) -> None:
    registry = workspace / "registry"
    registry.mkdir(parents=True)
    (registry / "skills.json").write_text(json.dumps(skills, ensure_ascii=False), encoding="utf-8")


def _skill(
    skill_id: str,
    name: str,
    description: str = "",
    *,
    aliases: list[str] | None = None,
    tags: dict[str, list[str]] | None = None,
    free_tags: list[str] | None = None,
    evidence_text: str = "",
) -> dict:
    return {
        "skill_id": skill_id,
        "name": name,
        "description": description,
        "source": "test",
        "source_url": "",
        "source_commit": "abc123",
        "path": f"skills/{skill_id}",
        "digest": skill_id,
        "tags": tags or {},
        "free_tags": free_tags or [],
        "aliases": aliases or [],
        "evidence": [
            {
                "source": "test",
                "skill_id": skill_id,
                "path": "SKILL.md",
                "commit": "abc123",
                "line_start": 1,
                "line_end": 2,
                "chunk_hash": skill_id,
                "text": evidence_text,
            }
        ]
        if evidence_text
        else [],
    }


def test_exact_alias_outranks_lexical_match(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            _skill(
                "citation-audit",
                "Citation Audit",
                aliases=["citecheck"],
                evidence_text="Audits bibliography entries and citation coverage.",
            ),
            _skill(
                "paper-review",
                "Paper Review",
                description="citecheck citecheck citecheck citation bibliography review",
                evidence_text="Strong lexical overlap for citecheck style review.",
            ),
        ],
    )

    candidates = route("please run citecheck before submission", tmp_path)

    assert [candidate.skill_id for candidate in candidates[:2]] == ["citation-audit", "paper-review"]
    assert candidates[0].reasons == ["exact alias match: citecheck"]
    assert candidates[0].evidence[0].text == "Audits bibliography entries and citation coverage."


def test_no_signal_returns_empty(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            _skill(
                "citation-audit",
                "Citation Audit",
                description="Check references and bibliography consistency.",
                tags={"task": ["citations"]},
            )
        ],
    )

    assert route("需要GPU算力跑实验", tmp_path) == []


def test_chinese_gpu_query_ranks_vast_gpu_first(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            _skill(
                "vast-gpu",
                "Vast GPU",
                description="租用GPU服务器和云算力来跑机器学习实验。",
                tags={"tool": ["GPU算力", "GPU服务器"], "task": ["实验"]},
                free_tags=["云算力"],
                evidence_text="Use when a project needs GPU算力 or GPU服务器 for experiments.",
            ),
            _skill(
                "aris-experiment",
                "ARIS Experiment",
                description="Plan and monitor machine learning experiments.",
                tags={"task": ["实验"]},
                evidence_text="Experiment planning workflow.",
            ),
        ],
    )

    candidates = route("需要GPU算力跑实验", tmp_path)

    assert [candidate.skill_id for candidate in candidates] == ["vast-gpu", "aris-experiment"]
    assert any("GPU算力" in reason for reason in candidates[0].reasons)
    assert candidates[0].evidence[0].text.startswith("Use when")


def test_mixed_chinese_english_query_uses_identity_token_boost(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            _skill(
                "experiment-bridge",
                "Experiment Bridge",
                tags={"tool": ["GPU算力"], "task": ["跑实验"]},
            ),
            _skill(
                "vast-gpu",
                "Vast GPU",
                tags={"tool": ["GPU算力"], "task": ["跑实验"]},
            ),
        ],
    )

    candidates = route("需要GPU算力跑实验", tmp_path)

    assert [candidate.skill_id for candidate in candidates] == ["vast-gpu", "experiment-bridge"]
    assert any("identity" in reason for reason in candidates[0].reasons)


def test_top_k_limit(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            _skill("one", "One", description="shared route term"),
            _skill("two", "Two", description="shared route term"),
            _skill("three", "Three", description="shared route term"),
        ],
    )

    candidates = route("shared route term", tmp_path, top_k=2)

    assert len(candidates) == 2
