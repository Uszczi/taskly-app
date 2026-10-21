from pathlib import Path

import pytest

from taskly_test_agent.skills import SKILLS_DIR, SkillError, load_skills, parse_skill


def write_skill(root: Path, dirname: str, text: str) -> Path:
    path = root / dirname / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(text)
    return path


def test_parses_frontmatter_and_body(tmp_path: Path) -> None:
    path = write_skill(tmp_path, "my-skill", "---\nname: my-skill\ndescription: Does X.\n---\n\n# Body\n")

    skill = parse_skill(path)

    assert (skill.name, skill.description, skill.body) == ("my-skill", "Does X.", "# Body")


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("# no frontmatter\n", "missing '---' frontmatter"),
        ("---\nname: Bad_Name\ndescription: d\n---\nbody\n", "kebab-case"),
        ("---\nname: other\ndescription: d\n---\nbody\n", "must match its directory"),
        ("---\nname: my-skill\n---\nbody\n", "'description' is required"),
        ("---\nname: my-skill\ndescription: d\n---\n\n", "body is empty"),
        ("---\n- a list\n---\nbody\n", "must be a mapping"),
    ],
)
def test_rejects_invalid_skills(tmp_path: Path, text: str, error: str) -> None:
    path = write_skill(tmp_path, "my-skill", text)

    with pytest.raises(SkillError, match=error):
        parse_skill(path)


def test_load_skills_is_sorted_by_name(tmp_path: Path) -> None:
    for name in ["zeta", "alpha"]:
        write_skill(tmp_path, name, f"---\nname: {name}\ndescription: d\n---\nbody\n")

    assert [s.name for s in load_skills(tmp_path)] == ["alpha", "zeta"]


def test_repository_skills_are_valid() -> None:
    """Guards the shipped SKILL.md files: a broken one would fail every agent run."""
    names = [s.name for s in load_skills(SKILLS_DIR)]

    assert names == ["backend-unit-tests", "frontend-unit-tests", "test-scope"]


def test_skill_becomes_deferred_capability(tmp_path: Path) -> None:
    path = write_skill(tmp_path, "my-skill", "---\nname: my-skill\ndescription: Does X.\n---\nbody\n")

    capability = parse_skill(path).to_capability()

    assert capability.id == "my-skill"
    assert capability.defer_loading is True
