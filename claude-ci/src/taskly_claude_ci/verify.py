from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from .git import status_entries
from .models import Report, Result, Run, Status
from .sandbox import run

Command = tuple[Literal["backend", "frontend", "typecheck"], Path, list[str]]


def is_writable_test(path: str) -> bool:
    if path.startswith("backend/tests/") and path.endswith(".py"):
        return True
    if path.startswith("frontend/src/test/") and path.endswith((".ts", ".tsx")):
        return True
    return path.startswith("frontend/src/") and path.endswith((".test.ts", ".test.tsx"))


def disk_changes(repo: Path) -> tuple[list[str], list[str]]:
    entries = iter(filter(None, status_entries(repo)))
    written: list[str] = []
    violations: list[str] = []
    for entry in entries:
        status, path = entry[:2], entry[3:]
        if "R" in status or "C" in status:
            # -z puts the original path of a rename or copy in the next entry
            next(entries)
            violations.append(path)
        elif "D" in status or (repo / path).is_symlink() or not is_writable_test(path):
            violations.append(path)
        else:
            written.append(path)
    return written, violations


def commands(repo: Path, written: list[str]) -> list[Command]:
    runs: list[Command] = []
    if any(p.startswith("backend/") for p in written):
        pytest = [".venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        runs.append(("backend", repo / "backend", pytest))
    if any(p.startswith("frontend/") for p in written):
        vitest = ["node_modules/.bin/vitest", "run"]
        runs.append(("frontend", repo / "frontend", vitest))
        tsc = ["node_modules/.bin/tsc", "--noEmit", "-p", "."]
        runs.append(("typecheck", repo / "frontend", tsc))
    return runs


def parse_report(text: str | None) -> Report | None:
    try:
        return Report.model_validate_json(text or "")
    except ValidationError:
        return None


def verify(
    repo: Path,
    logs: Path,
    report_text: str | None,
    conclusion: str,
) -> Result:
    written, violations = disk_changes(repo)
    report = parse_report(report_text)
    runs: list[Run] = []
    if not violations:
        for target, cwd, argv in commands(repo, written):
            runs.append(
                Run(
                    target=target,
                    exit_code=run(repo, cwd, argv, logs / f"{target}.log"),
                )
            )

    status: Status
    if violations:
        status = "violation"
    elif conclusion != "success" or report is None:
        status = "agent_failed"
    elif any(r.exit_code != 0 for r in runs):
        status = "tests_failed"
    else:
        status = "ok"

    return Result(
        status=status, written=written, violations=violations, runs=runs, report=report
    )
