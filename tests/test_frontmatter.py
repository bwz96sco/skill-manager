from pathlib import Path

from skill_manager.frontmatter import parse_frontmatter


def test_parse_quoted_description_with_colon(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        '---\nname: demo\ndescription: "Use when serverless: modal is needed"\n---\n# Body\n',
        encoding="utf-8",
    )

    metadata, body = parse_frontmatter(skill)

    assert metadata["name"] == "demo"
    assert metadata["description"] == "Use when serverless: modal is needed"
    assert body.startswith("# Body")
