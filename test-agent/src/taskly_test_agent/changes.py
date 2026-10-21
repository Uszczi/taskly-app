"""Deterministic analysis of which source files need tests. No model involved.

The model gets this plan as facts instead of exploring the repository itself:
cheaper, reproducible, and when nothing is testable the agent is not run at all.
The skip rules mirror the coverage exclusions in backend/pyproject.toml and
frontend/vite.config.ts; keep the three in sync.
"""

import re
import subprocess
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Literal

Area = Literal["backend", "frontend"]

_BACKEND_SKIP = ("__init__.py", "schemas.py", "models.py", "types.py", "constants.py")
# Only the entrypoint (`app = create_app()`); a main.py deeper in app/ may hold real logic.
_BACKEND_SKIP_PATHS = ("backend/app/main.py",)
_FRONTEND_SKIP_GLOBS = (
    "frontend/src/main.tsx",
    "frontend/src/test/*",
    "frontend/src/design-system/*",
    "*/types.ts",
    "*.types.ts",
    "*/index.ts",
    "*/constants.ts",
    "*/constants.tsx",
    "*.constants.ts",
    "*.d.ts",
    "*.stories.tsx",
    "frontend/src/features/todos/api/queryKeys.ts",
    "frontend/src/lib/queryClient.ts",
)
# A git ref or SHA from the CI event; never something that git could read as an option.
_SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/~^-]*$")


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class Target:
    """A source file that should have unit tests."""

    source: str
    area: Area
    test: str  # conventional test path, existing or to be created
    test_exists: bool


@dataclass(frozen=True)
class Skipped:
    path: str
    reason: str


@dataclass(frozen=True)
class Plan:
    targets: list[Target]
    skipped: list[Skipped]
    changed_tests: list[str]  # test files the change itself already touches

    @property
    def is_empty(self) -> bool:
        return not self.targets


def is_test_file(path: str) -> bool:
    return path.startswith("backend/tests/") or bool(re.search(r"\.test\.tsx?$", path))


def classify(path: str) -> tuple[Area, str] | Skipped:
    """(area, conventional test path) for testable sources, else Skipped with a reason."""
    if path.startswith("backend/app/") and path.endswith(".py"):
        if Path(path).name in _BACKEND_SKIP or path in _BACKEND_SKIP_PATHS:
            return Skipped(path, "excluded from backend coverage")
        rel = Path(path).relative_to("backend/app")
        return "backend", f"backend/tests/{rel.parent / f'test_{rel.name}'}"
    if path.startswith("frontend/src/") and path.endswith((".ts", ".tsx")):
        if any(fnmatch(path, glob) for glob in _FRONTEND_SKIP_GLOBS):
            return Skipped(path, "excluded from frontend coverage")
        stem, ext = path.rsplit(".", 1)
        return "frontend", f"{stem}.test.{ext}"
    return Skipped(path, "not backend or frontend source")


def build_plan(repo_root: Path, paths: list[str]) -> Plan:
    targets, skipped, changed_tests = [], [], []
    for path in sorted(set(paths)):
        if is_test_file(path):
            changed_tests.append(path)
            continue
        result = classify(path)
        if isinstance(result, Skipped):
            skipped.append(result)
            continue
        area, test = result
        targets.append(Target(path, area, test, (repo_root / test).is_file()))
    return Plan(targets, skipped, changed_tests)


def _git(repo_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo_root, capture_output=True, text=True, stdin=subprocess.DEVNULL
    )
    if proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git {args[0]} failed")
    return proc.stdout


def changed_paths(repo_root: Path, base: str, head: str = "HEAD") -> list[str]:
    """Files added, modified or renamed between the merge base of `base` and `head`.

    Deleted files are left out: there is nothing left to test.
    """
    for ref in (base, head):
        if not _SAFE_REF.match(ref):
            raise GitError(f"invalid git ref: {ref!r}")
    out = _git(repo_root, "diff", "--name-only", "-z", "--diff-filter=AMR", f"{base}...{head}", "--")
    return [p for p in out.split("\0") if p]


def tracked_paths(repo_root: Path) -> list[str]:
    out = _git(repo_root, "ls-files", "-z", "--", "backend/app", "frontend/src")
    return [p for p in out.split("\0") if p]


def plan_for_diff(repo_root: Path, base: str, head: str = "HEAD") -> Plan:
    """PR mode: the files a pull request changes."""
    return build_plan(repo_root, changed_paths(repo_root, base, head))


def plan_for_untested(repo_root: Path) -> Plan:
    """Backfill mode: every testable source file that has no test file yet."""
    plan = build_plan(repo_root, tracked_paths(repo_root))
    return Plan([t for t in plan.targets if not t.test_exists], [], [])


def render_task(plan: Plan) -> str:
    """The user prompt for the agent: the plan as facts plus what to do with it."""
    lines = ["Write or update unit tests for these source files.", ""]
    for t in plan.targets:
        state = "test exists, update it if the change is not covered" if t.test_exists else "no test yet"
        lines.append(f"- {t.source} ({t.area}) -> {t.test} [{state}]")
    if plan.changed_tests:
        lines += ["", "Test files already changed in this diff (check before duplicating them):"]
        lines += [f"- {p}" for p in plan.changed_tests]
    lines += [
        "",
        "Decide add/update/skip per source file following the `test-scope` skill, "
        "write tests at the listed test paths, and run them. Every test file you write "
        "ends either green or reported as a production bug. "
        "Report one decision per source file.",
    ]
    return "\n".join(lines)
