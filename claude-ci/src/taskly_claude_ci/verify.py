"""What Claude Code changed, checked from disk rather than from its report.

Runs after Claude with no model and no secrets. Claude's permissions already
limit edits to test files, but the tests it runs can write anywhere in the
checkout, so the verdict is decided here: every change must be a test file,
and the test files must pass when rerun together, typecheck included.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Literal, cast

from .models import Report, Result, Run, Status
from .plan import git

Command = tuple[Literal["backend", "frontend", "typecheck"], Path, list[str]]

# Test files Claude may not change, e.g. shared fixtures every test depends on. None for now.
PROTECTED: frozenset[str] = frozenset()
TIMEOUT_SECONDS = 600


def is_writable_test(path: str) -> bool:
    """Test files and the shared test code next to them: fixtures, mocks, helpers."""
    if path in PROTECTED:
        return False
    if path.startswith("backend/tests/") and path.endswith(".py"):
        return True
    if path.startswith("frontend/src/test/") and path.endswith((".ts", ".tsx")):
        return True
    return path.startswith("frontend/src/") and path.endswith((".test.ts", ".test.tsx"))


def is_test_file(path: str) -> bool:
    """A file the runner collects tests from, as opposed to shared test code."""
    if path.startswith("backend/"):
        return Path(path).name.startswith("test_")
    return path.endswith((".test.ts", ".test.tsx"))


def disk_changes(repo: Path) -> tuple[list[str], list[str]]:
    """(test files written, violations). Fails closed: deletes, renames and symlinks are violations."""
    entries = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").split("\0")
    written: list[str] = []
    violations: list[str] = []
    i = 0
    while i < len(entries) and entries[i]:
        status, path = entries[i][:2], entries[i][3:]
        i += 1
        if "R" in status or "C" in status:
            i += 1  # -z puts the original path of a rename or copy in the next entry
            violations.append(path)
        elif "D" in status or (repo / path).is_symlink() or not is_writable_test(path):
            violations.append(path)
        else:
            written.append(path)
    return written, violations


def sandboxed(repo: Path, cwd: Path, argv: list[str]) -> list[str]:
    """`argv` with an empty environment, no network and a read-only filesystem except the checkout."""
    env = [f"PATH={os.environ.get('PATH', '/usr/bin:/bin')}", f"HOME={os.environ.get('HOME', '/tmp')}",
           "NO_COLOR=1", "CI=1", "PYTHONDONTWRITEBYTECODE=1"]
    return ["env", "-i", *env, "bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
            "--tmpfs", "/tmp", "--bind", str(repo), str(repo), "--unshare-all", "--die-with-parent",
            "--chdir", str(cwd), "--", *argv]


def commands(repo: Path, written: list[str]) -> list[Command]:
    """(target, cwd, argv) for each run the written files need.

    Shared test code (a conftest.py, mocks, a helper in frontend/src/test/) can
    break tests Claude never touched, so changing any reruns the area's whole suite.
    """
    backend = [p for p in written if p.startswith("backend/")]
    frontend = [p for p in written if p.startswith("frontend/")]
    runs: list[Command] = []
    if backend:
        paths = backend if all(is_test_file(p) for p in backend) else ["backend/tests"]
        runs.append(("backend", repo, ["backend/.venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths]))
    if frontend:
        tests = [p.removeprefix("frontend/") for p in frontend] if all(is_test_file(p) for p in frontend) else []
        runs.append(("frontend", repo / "frontend", ["node_modules/.bin/vitest", "run", *tests]))
        # vitest strips types without checking them, so a test that does not compile can pass.
        runs.append(("typecheck", repo / "frontend", ["node_modules/.bin/tsc", "--noEmit", "-p", "."]))
    return runs


def run(repo: Path, cwd: Path, argv: list[str], log: Path, sandbox: bool = True) -> int:
    """Run one command, writing its output to `log`. `sandbox=False` is for tests only."""
    if sandbox:
        argv = sandboxed(repo, cwd, argv)
    try:
        proc = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, stdin=subprocess.DEVNULL
        )
    except subprocess.TimeoutExpired:
        log.write_text(f"Timed out after {TIMEOUT_SECONDS}s\n")
        return 124
    log.write_text(proc.stdout + proc.stderr)
    return proc.returncode


def parse_report(text: str | None) -> Report | None:
    """Claude's structured output; the action already checked it against the shared schema."""
    try:
        report = json.loads(text or "")
    except ValueError:
        return None
    # The fields are model text; the action has only checked their shape.
    return cast(Report, report) if isinstance(report, dict) else None


def verify(repo: Path, out: Path, report_text: str | None, conclusion: str, sandbox: bool = True) -> Status:
    """Write result.json (and tests.patch, run logs); return the status."""
    written, violations = disk_changes(repo)
    report = parse_report(report_text)
    runs: list[Run] = []
    # With a violation nothing is committed, so its tests are not worth running.
    if not violations:
        for target, cwd, argv in commands(repo, written):
            runs.append(Run(target=target, exit_code=run(repo, cwd, argv, out / f"{target}.log", sandbox)))

    status: Status
    if violations:
        status = "violation"
    elif conclusion != "success" or report is None:
        status = "agent_failed"
    elif any(r["exit_code"] != 0 for r in runs):
        status = "tests_failed"
    else:
        status = "ok"

    result = Result(status=status, written=written, violations=violations, runs=runs, report=report)
    (out / "result.json").write_text(json.dumps(result, indent=2))
    if written:
        git(repo, "add", "--", *written)
        (out / "tests.patch").write_text(git(repo, "diff", "--cached", "--binary"))
    return status

