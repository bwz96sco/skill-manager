from __future__ import annotations

import json
from pathlib import Path

from skill_manager.evals import run


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _skill(
    skill_id: str,
    description: str,
    *,
    aliases: list[str] | None = None,
    tags: dict[str, list[str]] | None = None,
) -> dict:
    return {
        "skill_id": skill_id,
        "name": skill_id.replace("-", " ").title(),
        "description": description,
        "source": "test",
        "source_url": "",
        "source_commit": "abc123",
        "path": f"skills/{skill_id}",
        "digest": skill_id,
        "tags": tags or {},
        "free_tags": [],
        "aliases": aliases or [],
        "evidence": [],
    }


def test_run_computes_metrics_and_empty_expected_false_positive(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "registry" / "skills.json",
        {
            "skills": [
                _skill(
                    "vast-gpu",
                    "GPU算力 GPU服务器 云算力 experiments",
                    tags={"tool": ["GPU算力", "GPU服务器"]},
                ),
                _skill("citation-audit", "bibliography citation audit", aliases=["citecheck"]),
                _skill("paper-review", "review paper claims"),
            ]
        },
    )
    _write_json(
        tmp_path / "evals" / "goldens.json",
        {
            "rows": [
                {"query": "需要GPU算力跑实验", "expected": ["vast-gpu"]},
                {"query": "please run citecheck", "expected": ["citation-audit"]},
                {"query": "citation bibliography", "expected": ["citation-audit", "paper-review"]},
                {"query": "GPU服务器", "expected": []},
            ]
        },
    )

    result = run(tmp_path, top_k=2)

    assert result["rows"] == 4
    assert result["evaluated_rows"] == 3
    assert result["empty_expected_rows"] == 1
    assert result["false_positive_like"] == 1
    assert result["hit_at_1"] == 1.0
    assert result["recall_at_3"] == 5 / 6
    assert result["recall_at_5"] == 5 / 6
    assert result["details"][3]["expected"] == []
    assert result["details"][3]["predicted"] == ["vast-gpu"]
