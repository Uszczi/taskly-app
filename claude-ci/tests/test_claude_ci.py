import json
import subprocess
import sys
from pathlib import Path

import pytest

from taskly_claude_ci import coverage as coverage_module
from taskly_claude_ci import sandbox
from taskly_claude_ci import verify as verify_module
from taskly_claude_ci.comment import render
from taskly_claude_ci.coverage import measure
from taskly_claude_ci.github import multiline_output
from taskly_claude_ci.models import (
    AreaCoverage,
    Coverage,
    Plan,
    Report,
    Result,
    Skipped,
    SkipRules,
)
from taskly_claude_ci.plan import build_plan, classify
from taskly_claude_ci.verify import disk_changes, verify

RULES = SkipRules.model_validate_json(
    (
        Path(__file__).parents[2] / ".github/claude-test-agent/skip-rules.json"
    ).read_text()
)
REPORT = json.dumps(
    {"summary": "Adds tests", "decisions": [], "attention": [], "skills_used": []}
)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture(autouse=True)
def no_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "sandboxed", lambda repo, cwd, argv: argv)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for path in ["backend/app/x.py", "backend/tests/test_old.py", "README.md"]:
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text("x = 1\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base")
    git(repo, "checkout", "-q", "-b", "feature")
    return repo


def commit(repo: Path, files: dict[str, str]) -> None:
    for path, text in files.items():
        (repo / path).write_text(text)
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "-m",
        "change",
    )


@pytest.mark.parametrize(
    ("path", "test"),
    [
        ("backend/app/api/deps.py", "backend/tests/api/test_deps.py"),
        ("frontend/src/App.tsx", "frontend/src/App.test.tsx"),
        ("backend/app/schemas.py", None),
        ("README.md", None),
    ],
)
def test_classify(path: str, test: str | None) -> None:
    entry = classify(path, RULES)
    assert (entry[1] if isinstance(entry, tuple) else None) == test


def test_plan_lists_changed_sources_with_their_diffs(repo: Path) -> None:
    commit(repo, {"backend/app/x.py": "x = 2\n", "README.md": "docs\n"})

    plan = build_plan(repo, "main", RULES)

    assert [(t.source, t.test, t.test_exists) for t in plan.targets] == [
        ("backend/app/x.py", "backend/tests/test_x.py", False)
    ]
    assert "+x = 2" in plan.targets[0].diff
    assert [s.path for s in plan.skipped] == ["README.md"]


def test_plan_rejects_refs_git_could_read_as_options(repo: Path) -> None:
    with pytest.raises(ValueError):
        build_plan(repo, "--output=/tmp/x", RULES)


def test_only_regular_test_files_are_written(repo: Path) -> None:
    (repo / "backend/tests/test_new.py").write_text("def test_x(): pass\n")
    (repo / "backend/app/x.py").write_text("x = 2\n")
    (repo / "backend/tests/test_old.py").unlink()
    (repo / "backend/tests/test_link.py").symlink_to("/etc/passwd")

    written, violations = disk_changes(repo)

    assert written == ["backend/tests/test_new.py"]
    assert sorted(violations) == [
        "backend/app/x.py",
        "backend/tests/test_link.py",
        "backend/tests/test_old.py",
    ]


@pytest.mark.parametrize(
    ("exit_code", "report", "conclusion", "status"),
    [
        (0, REPORT, "success", "ok"),
        (1, REPORT, "success", "tests_failed"),
        (0, '{"summary": "no other fields"}', "success", "agent_failed"),
        (0, REPORT, "failure", "agent_failed"),
    ],
)
def test_verify_status(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code: int,
    report: str,
    conclusion: str,
    status: str,
) -> None:
    command = [sys.executable, "-c", f"raise SystemExit({exit_code})"]
    monkeypatch.setattr(
        verify_module, "commands", lambda repo, written: [("backend", repo, command)]
    )
    (repo / "backend/tests/test_new.py").write_text("def test_x(): pass\n")

    assert verify(repo, tmp_path, report, conclusion).status == status


def test_reported_tests_that_were_never_written_fail_the_agent(
    repo: Path, tmp_path: Path
) -> None:
    decision = {"path": "backend/app/x.py", "action": "add", "reason": "r"}
    report = json.dumps({**json.loads(REPORT), "decisions": [decision]})

    assert verify(repo, tmp_path, report, "success").status == "agent_failed"


def test_a_violation_runs_no_tests(repo: Path, tmp_path: Path) -> None:
    (repo / "backend/app/x.py").write_text("x = 2\n")

    result = verify(repo, tmp_path, REPORT, "success")

    assert (result.status, result.runs) == ("violation", [])


def test_multiline_output_ends_at_a_random_delimiter() -> None:
    first, second = (
        multiline_output("prompt", "a\nEOF"),
        multiline_output("prompt", "a"),
    )
    delimiter = first.splitlines()[-1]

    assert (
        first == f"prompt<<{delimiter}\na\nEOF\n{delimiter}"
        and delimiter.startswith("EOF_")
    )
    assert delimiter != second.splitlines()[-1]


def test_coverage_keeps_only_changed_files(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit(repo, {"backend/app/x.py": "x = 2\n"})

    def fake_run(repo_dir: Path, cwd: Path, argv: list[str], log: Path) -> int:
        report = repo_dir / "backend/coverage/coverage.json"
        report.parent.mkdir()
        files = {"app/x.py": 40.0, "app/other.py": 90.0}
        report.write_text(
            json.dumps(
                {
                    "totals": {"percent_covered": 70.0},
                    "files": {
                        path: {"summary": {"percent_covered": pct}}
                        for path, pct in files.items()
                    },
                }
            )
        )
        return 1

    monkeypatch.setattr(coverage_module, "run", fake_run)

    measured = measure(repo, "main", tmp_path)

    assert measured.backend == AreaCoverage(
        total=70.0, files={"backend/app/x.py": 40.0}
    )
    assert not (repo / "backend/coverage").exists()


def test_comment_shows_tests_coverage_and_skips_with_model_text_made_safe() -> None:
    patch = "diff --git a/backend/tests/test_x.py b/backend/tests/test_x.py\n+def test_rejects_empty_title():\n"
    report = Report(
        summary="Covers x @team <b>",
        decisions=[],
        attention=["check <i>this</i>"],
        skills_used=[],
    )
    plan = Plan(
        skipped=[
            Skipped(path="backend/app/schemas.py", reason="excluded", excluded=True)
        ]
    )
    after = Coverage(backend=AreaCoverage(total=90.0, files={}))

    body = render(
        Result(status="ok", report=report),
        plan,
        patch,
        Coverage(),
        after,
        "https://run",
        "m",
        denied=2,
    )

    assert "✅ 1 test added, passing" in body
    assert "- `backend/tests/test_x.py`\n  - rejects empty title" in body
    assert "| **backend total** | – | 90% |  |" in body
    assert "| `backend/app/schemas.py` | excluded |" in body
    assert "@​team" in body and "<b>" not in body and "<i>" not in body
    assert "Claude Code denied 2 tool call(s)" in body


def test_comment_without_a_result_says_verification_did_not_run() -> None:
    body = render(None, Plan(), "", Coverage(), Coverage(), "https://run", "m")

    assert "failed before Claude's work was verified" in body
