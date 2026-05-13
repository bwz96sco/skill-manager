from __future__ import annotations

from pathlib import Path
from typing import Any

from .routing import route
from .workspace import Workspace, read_json


def run(workspace: str | Path | Workspace | None = None, top_k: int = 5) -> dict[str, Any]:
    ws = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    rows = _load_rows(ws)

    evaluated = 0
    hit_at_1 = 0
    recall_at_3_total = 0.0
    recall_at_5_total = 0.0
    empty_expected_rows = 0
    false_positive_like = 0
    details: list[dict[str, Any]] = []

    route_limit = max(top_k, 5)
    for row in rows:
        query = str(row.get("query", ""))
        expected = [str(item) for item in row.get("expected", []) if item is not None]
        candidates = route(query, ws, top_k=route_limit)
        predicted = [candidate.skill_id for candidate in candidates]

        if expected:
            evaluated += 1
            expected_set = set(expected)
            if predicted[:1] and predicted[0] in expected_set:
                hit_at_1 += 1
            recall_at_3_total += _recall(predicted[:3], expected_set)
            recall_at_5_total += _recall(predicted[:5], expected_set)
        else:
            empty_expected_rows += 1
            if candidates:
                false_positive_like += 1

        details.append(
            {
                "query": query,
                "expected": expected,
                "predicted": predicted[:top_k],
                "hit_at_1": bool(expected and predicted[:1] and predicted[0] in set(expected)),
                "recall_at_3": _recall(predicted[:3], set(expected)) if expected else None,
                "recall_at_5": _recall(predicted[:5], set(expected)) if expected else None,
            }
        )

    return {
        "rows": len(rows),
        "evaluated_rows": evaluated,
        "empty_expected_rows": empty_expected_rows,
        "hit_at_1": hit_at_1 / evaluated if evaluated else 0.0,
        "recall_at_3": recall_at_3_total / evaluated if evaluated else 0.0,
        "recall_at_5": recall_at_5_total / evaluated if evaluated else 0.0,
        "false_positive_like": false_positive_like,
        "details": details,
    }


def _load_rows(workspace: Workspace) -> list[dict[str, Any]]:
    payload = read_json(workspace.evals / "goldens.json", [])
    if isinstance(payload, dict):
        raw_rows = payload.get("rows", [])
    else:
        raw_rows = payload
    if not isinstance(raw_rows, list):
        return []
    return [row for row in raw_rows if isinstance(row, dict)]


def _recall(predicted: list[str], expected: set[str]) -> float:
    if not expected:
        return 0.0
    return len(set(predicted) & expected) / len(expected)
