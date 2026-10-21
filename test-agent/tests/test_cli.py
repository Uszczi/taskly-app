import json
import subprocess
import sys
from pathlib import Path

import pytest

from taskly_test_agent import unverified_tests, verify_written_tests
from taskly_test_agent.paths import PathNotAllowed
from taskly_test_agent.runner import TestRun


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "README.md").write_text("x\n")
    (tmp_path / "backend/app").mkdir(parents=True)
    (tmp_path / "backend/app/factory.py").write_text("x = 1\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "feature")
    return tmp_path


def cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {"PATH": "/usr/bin:/bin", "PYDANTIC_AI_NO_BANNER": "1"}  # no AGENT_MODEL, no API keys
    return subprocess.run(
        [sys.executable, "-c", "from taskly_test_agent import main; main()", "--repo", str(repo), *args],
        capture_output=True, text=True, env=env,
    )


def test_docs_only_change_skips_the_agent_without_a_model(repo: Path) -> None:
    (repo / "README.md").write_text("y\n")
    git(repo, "commit", "-q", "-am", "docs")

    proc = cli(repo, "--diff", "main")

    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["agent_ran"] is False
    assert out["plan"]["skipped"] == [
        {"path": "README.md", "reason": "not backend or frontend source", "excluded": False}
    ]


def test_plan_only_lists_targets_without_a_model(repo: Path) -> None:
    (repo / "backend/app/factory.py").write_text("x = 2\n")
    git(repo, "commit", "-q", "-am", "code")

    proc = cli(repo, "--diff", "main", "--plan-only")

    assert proc.returncode == 0, proc.stderr
    targets = json.loads(proc.stdout)["plan"]["targets"]
    assert targets == [{
        "source": "backend/app/factory.py", "area": "backend",
        "test": "backend/tests/test_factory.py", "test_exists": False,
    }]


def test_testable_change_requires_a_model(repo: Path) -> None:
    (repo / "backend/app/factory.py").write_text("x = 2\n")
    git(repo, "commit", "-q", "-am", "code")

    proc = cli(repo, "--diff", "main")

    assert proc.returncode == 2
    assert "set --model or AGENT_MODEL" in proc.stderr


def test_bad_base_ref_is_a_config_error(repo: Path) -> None:
    proc = cli(repo, "--diff", "no-such-branch")

    assert proc.returncode == 3
    assert proc.stderr.startswith("error [git]:")


def test_written_tests_are_rerun_together_per_area() -> None:
    calls = []

    def fake_run(repo_root, target, paths):
        calls.append((target, paths))
        return TestRun(target, tuple(paths), 0 if target == "backend" else 1, "")

    written = [
        "backend/tests/__init__.py",
        "backend/tests/test_a.py",
        "frontend/src/a.test.ts",
        "backend/tests/test_b.py",
        "frontend/src/b.test.tsx",
    ]
    runs = verify_written_tests(Path("."), written, run=fake_run)

    # __init__.py is not a test; each area runs once with every file it got.
    assert calls == [
        ("backend", ["backend/tests/test_a.py", "backend/tests/test_b.py"]),
        ("frontend", ["frontend/src/a.test.ts", "frontend/src/b.test.tsx"]),
    ]
    assert unverified_tests(runs) == ["frontend/src/a.test.ts", "frontend/src/b.test.tsx"]


def test_a_test_file_that_cannot_be_run_is_unverified() -> None:
    def refuse(repo_root, target, paths):
        raise PathNotAllowed("gone")

    runs = verify_written_tests(Path("."), ["backend/tests/test_a.py"], run=refuse)

    assert unverified_tests(runs) == ["backend/tests/test_a.py"]


def test_nothing_written_needs_no_verification() -> None:
    assert verify_written_tests(Path("."), []) == []
