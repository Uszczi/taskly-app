from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext

from .paths import PathNotAllowed, is_secret, is_test_path, resolve_in_repo
from .runner import Target, TestRun, run_tests as run_test_suite
from .shared import INSTRUCTIONS, REPORT_SCHEMA
from .skills import load_skills

MAX_FILE_CHARS = 40_000
MAX_WRITE_CHARS = 60_000


@dataclass
class Deps:
    repo_root: Path
    # Recorded by the tools themselves, so the final report states what actually
    # happened rather than what the model claims happened.
    written: list[str] = field(default_factory=list)
    test_runs: list[TestRun] = field(default_factory=list)


# Descriptions come from the shared report schema, which Claude Code gets as its
# --json-schema; test_report_matches_the_shared_schema keeps the structure in step.
_FIELDS = REPORT_SCHEMA["properties"]
_DECISION_FIELDS = _FIELDS["decisions"]["items"]["properties"]


class FileDecision(BaseModel):
    path: str = Field(description=_DECISION_FIELDS["path"]["description"])
    action: Literal["add", "update", "skip"]
    reason: str


class Report(BaseModel):
    summary: str = Field(description=_FIELDS["summary"]["description"])
    decisions: list[FileDecision] = Field(default_factory=list, description=_FIELDS["decisions"]["description"])
    attention: list[str] = Field(default_factory=list, description=_FIELDS["attention"]["description"])
    skills_used: list[str] = Field(default_factory=list, description=_FIELDS["skills_used"]["description"])


agent = Agent(
    name="taskly_test_agent",
    deps_type=Deps,
    output_type=Report,
    instructions=INSTRUCTIONS,  # shared with Claude Code; this engine's specifics are in the tools
    capabilities=[skill.to_capability() for skill in load_skills()],
)


@agent.tool
def read_file(ctx: RunContext[Deps], path: str) -> str:
    """Read a text file from the repository.

    Args:
        path: Path relative to the repository root, e.g. `backend/app/factory.py`.
    """
    try:
        file = resolve_in_repo(ctx.deps.repo_root, path)
    except PathNotAllowed as exc:
        raise ModelRetry(str(exc)) from exc
    if is_secret(ctx.deps.repo_root, file):
        raise ModelRetry(f"{path!r} may contain secrets and cannot be read")
    if not file.is_file():
        raise ModelRetry(f"{path!r} is not a file")
    text = file.read_text(errors="replace")
    if len(text) > MAX_FILE_CHARS:
        text = text[:MAX_FILE_CHARS] + "\n... [truncated]"
    return text


@agent.tool
def list_dir(ctx: RunContext[Deps], path: str = ".") -> list[str]:
    """List entries of a repository directory (directories end with `/`).

    Args:
        path: Directory relative to the repository root, e.g. `backend/app`.
    """
    try:
        directory = resolve_in_repo(ctx.deps.repo_root, path)
    except PathNotAllowed as exc:
        raise ModelRetry(str(exc)) from exc
    if not directory.is_dir():
        raise ModelRetry(f"{path!r} is not a directory")
    skip = {".git", "node_modules", ".venv", "__pycache__"}
    return sorted(
        f"{p.name}/" if p.is_dir() else p.name
        for p in directory.iterdir()
        if p.name not in skip
    )


@agent.tool
def write_test_file(ctx: RunContext[Deps], path: str, content: str) -> str:
    """Create or overwrite a unit test file. Only test files may be written.

    Allowed: `backend/tests/**/*.py` (except conftest.py and mocks.py at the
    tests root) and `frontend/src/**/*.test.ts(x)`. Always send the full file.

    Args:
        path: Test file path relative to the repository root.
        content: Complete new content of the file.
    """
    try:
        file = resolve_in_repo(ctx.deps.repo_root, path)
    except PathNotAllowed as exc:
        raise ModelRetry(str(exc)) from exc
    if not is_test_path(ctx.deps.repo_root, file):
        raise ModelRetry(f"{path!r} is not a writable test file; production code is off limits")
    if len(content) > MAX_WRITE_CHARS:
        raise ModelRetry(f"File too large ({len(content)} chars); split it into smaller test files")
    file.parent.mkdir(parents=True, exist_ok=True)
    for package in _missing_test_packages(ctx.deps.repo_root, file):
        package.touch()
        _record_write(ctx.deps, package)
    file.write_text(content)
    rel = _record_write(ctx.deps, file)
    return f"Wrote {rel} ({len(content.splitlines())} lines)"


def _missing_test_packages(repo_root: Path, file: Path) -> list[Path]:
    """`__init__.py` files missing between backend/tests and `file`.

    backend/tests is a package tree; a directory without `__init__.py` makes
    pytest import same-named test modules (e.g. two test_router.py) as one.
    """
    tests_root = repo_root.resolve() / "backend/tests"
    if tests_root not in file.parents:
        return []
    missing = []
    directory = file.parent
    while directory != tests_root:
        if not (directory / "__init__.py").exists():
            missing.append(directory / "__init__.py")
        directory = directory.parent
    return missing


def _record_write(deps: Deps, file: Path) -> str:
    rel = file.relative_to(deps.repo_root.resolve()).as_posix()
    if rel not in deps.written:
        deps.written.append(rel)
    return rel


@agent.tool
def run_tests(ctx: RunContext[Deps], target: Target, paths: list[str]) -> str:
    """Run unit tests and return the exit code and the (tail of the) output.

    Run the files you wrote or changed. Fix failing tests you wrote; if a test
    fails because the production code is wrong, keep the test and report it.
    A frontend run also typechecks the project with `tsc --noEmit` and passes
    only when both pass: fix type errors in your test files too. After you
    finish, every file you wrote is rerun together, so end on a run of all of them.

    Args:
        target: `backend` (pytest) or `frontend` (vitest, then tsc).
        paths: Test files relative to the repository root, e.g.
            `backend/tests/api/test_health.py` or `frontend/src/hooks/useX.test.ts`.
    """
    if not paths:
        raise ModelRetry("Pass the test files to run")
    try:
        result = run_test_suite(ctx.deps.repo_root, target, paths)
    except PathNotAllowed as exc:
        raise ModelRetry(str(exc)) from exc
    ctx.deps.test_runs.append(result)
    status = "PASSED" if result.passed else "FAILED"
    return f"{status} (exit code {result.exit_code})\n{result.output}"
