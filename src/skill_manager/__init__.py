from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .models import to_jsonable


def _workspace_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", help="Skill manager workspace; defaults to ~/.skill-manager")


def _print_json(payload: Any) -> None:
    print(json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillmgr",
        description="Local-first skill subscription, derivation, and advisory routing manager.",
    )
    _workspace_arg(parser)
    subcommands = parser.add_subparsers(dest="command", required=True)

    source = subcommands.add_parser("source", help="Manage subscribed skill sources")
    source_sub = source.add_subparsers(dest="source_command", required=True)
    source_add = source_sub.add_parser("add", help="Add a git-backed skill source")
    source_add.add_argument("name")
    source_add.add_argument("url")
    source_add.add_argument("--path", default=".", help="Skill root inside the repository")
    source_add.add_argument("--ref", default="main")
    source_update = source_sub.add_parser("update", help="Update one source or all sources")
    source_update.add_argument("name", nargs="?")

    subcommands.add_parser("scan", help="Scan subscribed sources into the skill registry")

    route_cmd = subcommands.add_parser("route", help="Recommend skills for a natural-language task")
    route_cmd.add_argument("query")
    route_cmd.add_argument("--project")
    route_cmd.add_argument("--top-k", type=int, default=5)

    derive = subcommands.add_parser("derive", help="Propose or approve meta-skill drafts")
    derive_sub = derive.add_subparsers(dest="derive_command", required=True)
    derive_sub.add_parser("propose")
    derive_approve = derive_sub.add_parser("approve")
    derive_approve.add_argument("draft_id")

    project = subcommands.add_parser("project", help="Generate project-specific skill drafts")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    project_propose = project_sub.add_parser("propose")
    project_propose.add_argument("--project", required=True)

    export = subcommands.add_parser("export", help="Install approved generated skills")
    export_sub = export.add_subparsers(dest="export_command", required=True)
    export_apply = export_sub.add_parser("apply")
    export_apply.add_argument("draft_id")
    export_apply.add_argument("--target", required=True, choices=["agents", "claude", "codex", "project"])
    export_apply.add_argument("--dest")

    eval_cmd = subcommands.add_parser("eval", help="Run routing golden evals")
    eval_sub = eval_cmd.add_subparsers(dest="eval_command", required=True)
    eval_sub.add_parser("run")

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    workspace = args.workspace

    if args.command == "source":
        from .sources import add_source, update_sources

        if args.source_command == "add":
            _print_json(add_source(args.name, args.url, args.path, args.ref, workspace))
            return
        if args.source_command == "update":
            _print_json({"changed": update_sources(args.name, workspace)})
            return

    if args.command == "scan":
        from .sources import scan_sources

        _print_json({"skills": scan_sources(workspace)})
        return

    if args.command == "route":
        from .routing import route

        _print_json({"candidates": route(args.query, workspace, args.project, args.top_k)})
        return

    if args.command == "derive":
        from .derive import approve, propose

        if args.derive_command == "propose":
            _print_json({"drafts": propose(workspace)})
            return
        if args.derive_command == "approve":
            _print_json(approve(args.draft_id, workspace))
            return

    if args.command == "project":
        from .project import propose

        _print_json(propose(Path(args.project), workspace))
        return

    if args.command == "export":
        from .export import apply

        _print_json(apply(args.draft_id, args.target, workspace, args.dest))
        return

    if args.command == "eval":
        from .evals import run

        _print_json(run(workspace))
        return

    parser.error("Unhandled command")


__all__ = ["build_parser", "main"]
