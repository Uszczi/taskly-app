import shutil
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, TypeAdapter

from .git import changed_files
from .json import read_json
from .models import AreaCoverage, Coverage
from .sandbox import run


class Percent(BaseModel):
    percent_covered: float


class PytestFile(BaseModel):
    summary: Percent


class PytestReport(BaseModel):
    totals: Percent
    files: dict[str, PytestFile]


class Lines(BaseModel):
    pct: Annotated[
        float | None, BeforeValidator(lambda v: None if v == "Unknown" else v)
    ]


class VitestFile(BaseModel):
    lines: Lines


VitestSummary = TypeAdapter(dict[str, VitestFile])


def _backend(repo: Path, log: Path, changed: list[str]) -> AreaCoverage | None:
    report = repo / "backend/coverage/coverage.json"
    argv = [
        ".venv/bin/python",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--cov",
        f"--cov-report=json:{report}",
    ]
    run(repo, repo / "backend", argv, log)
    data = read_json(report, PytestReport)
    shutil.rmtree(repo / "backend/coverage", ignore_errors=True)
    (repo / "backend/.coverage").unlink(missing_ok=True)
    if data is None:
        return None
    pcts = {
        f"backend/{path}": f.summary.percent_covered for path, f in data.files.items()
    }
    files = {path: pct for path, pct in pcts.items() if path in changed}
    return AreaCoverage(total=data.totals.percent_covered, files=files)


def _frontend(repo: Path, log: Path, changed: list[str]) -> AreaCoverage | None:
    argv = [
        "node_modules/.bin/vitest",
        "run",
        "--coverage",
        "--coverage.reporter=json-summary",
        "--coverage.reportOnFailure",
    ]
    run(repo, repo / "frontend", argv, log)
    summary = repo / "frontend/coverage/coverage-summary.json"
    try:
        data = VitestSummary.validate_json(summary.read_text())
    except (OSError, ValueError):
        return None
    finally:
        shutil.rmtree(repo / "frontend/coverage", ignore_errors=True)
    total = data.pop("total", None)
    if total is None or total.lines.pct is None:
        return None
    files = {
        rel: f.lines.pct
        for path, f in data.items()
        if f.lines.pct is not None
        and (rel := str(Path(path).relative_to(repo))) in changed
    }
    return AreaCoverage(total=total.lines.pct, files=files)


def measure(repo: Path, base: str, logs: Path) -> Coverage:
    changed = changed_files(repo, base, "backend/app", "frontend/src")
    coverage = Coverage()
    if any(p.startswith("backend/") for p in changed):
        coverage.backend = _backend(repo.resolve(), logs / "backend.log", changed)
    if any(p.startswith("frontend/") for p in changed):
        coverage.frontend = _frontend(repo.resolve(), logs / "frontend.log", changed)
    return coverage
