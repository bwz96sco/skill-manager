from skill_manager import build_parser


def test_cli_accepts_route_command() -> None:
    args = build_parser().parse_args(["--workspace", "/tmp/x", "route", "use citation audit"])

    assert args.workspace == "/tmp/x"
    assert args.command == "route"
    assert args.query == "use citation audit"
