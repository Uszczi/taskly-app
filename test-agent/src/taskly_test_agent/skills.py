"""Load Agent Skills (`<dir>/<name>/SKILL.md`) as deferred PydanticAI capabilities.

Only each skill's name and description reach the model up front; the body is
returned when the model calls the framework's `load_capability` tool. This keeps
the base prompt small and lets the same SKILL.md files work in other agents
that follow the open Agent Skills format.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic_ai.capabilities import Capability

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"

_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)


class SkillError(ValueError):
    pass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str

    def to_capability(self) -> Capability:
        return Capability(
            id=self.name,
            description=self.description,
            instructions=self.body,
            defer_loading=True,
        )


def parse_skill(path: Path) -> Skill:
    match = _FRONTMATTER.match(path.read_text())
    if not match:
        raise SkillError(f"{path}: missing '---' frontmatter block")
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise SkillError(f"{path}: frontmatter must be a mapping")

    name, description = meta.get("name"), meta.get("description")
    if not isinstance(name, str) or not _NAME.match(name):
        raise SkillError(f"{path}: 'name' must be lowercase kebab-case")
    if name != path.parent.name:
        raise SkillError(f"{path}: name {name!r} must match its directory")
    if not isinstance(description, str) or not description.strip():
        raise SkillError(f"{path}: 'description' is required")

    body = match.group(2).strip()
    if not body:
        raise SkillError(f"{path}: skill body is empty")
    return Skill(name=name, description=description.strip(), body=body)


def load_skills(directory: Path = SKILLS_DIR) -> list[Skill]:
    """All skills in `directory`, sorted by name so the prompt prefix stays cacheable."""
    return sorted(
        (parse_skill(p) for p in directory.glob("*/SKILL.md")),
        key=lambda skill: skill.name,
    )
