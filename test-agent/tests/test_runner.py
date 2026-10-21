import os
import sys
from pathlib import Path

import pytest

import shutil

from taskly_test_agent import runner, sandbox
from taskly_test_agent.paths import PathNotAllowed
from taskly_test_agent.runner import build_command, run_tests


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A tiny repo with one backend test; pytest runs with this interpreter."""
    (tmp_path / "pytest.ini").write_text("[pytest]\npythonpath = backend\n")
    tests = tmp_path / "backend/tests"
    tests.mkdir(parents=True)
    (tests / "test_ok.py").write_text("def test_ok():\n    assert 1 + 1 == 2\n")
    (tests / "test_bad.py").write_text("def test_bad():\n    assert 1 == 2\n")
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/a.test.ts").write_text("")
    monkeypatch.setenv("BACKEND_PYTHON", sys.executable)
    return tmp_path


def test_backend_command_is_fixed_and_repo_relative(repo: Path) -> None:
    argv, cwd, _ = build_command(repo, "backend", ["backend/tests/test_ok.py"])

    assert argv == [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "backend/tests/test_ok.py"]
    assert cwd == repo


def test_frontend_command_uses_local_vitest_binary(repo: Path) -> None:
    argv, cwd, _ = build_command(repo, "frontend", ["frontend/src/a.test.ts"])

    assert argv == [str(repo / "frontend/node_modules/.bin/vitest"), "run", "src/a.test.ts"]
    assert cwd == repo / "frontend"


@pytest.mark.parametrize(
    ("target", "path"),
    [
        ("backend", "--cov=/etc"),  # option injection
        ("backend", "backend/app/main.py"),  # production code
        ("backend", "frontend/src/a.test.ts"),  # wrong target
        ("frontend", "backend/tests/test_ok.py"),
        ("backend", "../outside.py"),
        ("backend", "backend/tests/test_missing.py"),
    ],
)
def test_rejects_paths_that_are_not_existing_target_tests(repo: Path, target, path: str) -> None:
    with pytest.raises(PathNotAllowed):
        build_command(repo, target, [path])


def test_runs_passing_and_failing_tests(repo: Path) -> None:
    ok = run_tests(repo, "backend", ["backend/tests/test_ok.py"])
    bad = run_tests(repo, "backend", ["backend/tests/test_bad.py"])

    assert ok.passed and "1 passed" in ok.output
    assert not bad.passed and "assert 1 == 2" in bad.output


def test_tests_do_not_see_secrets_from_agent_environment(repo: Path, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    (repo / "backend/tests/test_env.py").write_text(
        "import os\ndef test_env():\n    assert 'ANTHROPIC_API_KEY' not in os.environ\n"
    )

    assert run_tests(repo, "backend", ["backend/tests/test_env.py"]).passed


def test_timeout_is_reported(repo: Path, monkeypatch) -> None:
    monkeypatch.setattr(runner, "TIMEOUT_SECONDS", 1)
    (repo / "backend/tests/test_slow.py").write_text("import time\ndef test_slow():\n    time.sleep(5)\n")

    result = run_tests(repo, "backend", ["backend/tests/test_slow.py"])

    assert result.exit_code is None and "Timed out" in result.output


def test_long_output_keeps_the_tail(monkeypatch) -> None:
    monkeypatch.setattr(runner, "MAX_OUTPUT_CHARS", 10)

    assert runner._tail("x" * 50 + "SUMMARY") == "... [truncated]\n" + ("x" * 3 + "SUMMARY")


def test_relative_repo_root_uses_absolute_backend_interpreter(repo: Path, monkeypatch) -> None:
    monkeypatch.delenv("BACKEND_PYTHON")
    venv_python = repo / "backend/.venv/bin/python"
    venv_python.parent.mkdir(parents=True)
    # A wrapper, not a symlink: a symlinked venv interpreter loses its site-packages.
    venv_python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    venv_python.chmod(0o755)
    monkeypatch.chdir(repo / "backend")

    argv, cwd, _ = build_command(Path(".."), "backend", ["backend/tests/test_ok.py"])

    assert Path(argv[0]).is_absolute() and cwd.is_absolute()
    assert run_tests(Path(".."), "backend", ["backend/tests/test_ok.py"]).passed


def test_vitest_excludes_other_files_matched_by_the_substring_filter(repo: Path) -> None:
    for rel in ("a.test.tsx", "x/src/a.test.ts", "b.test.ts"):
        (repo / "frontend/src" / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / "frontend/src" / rel).write_text("")

    argv, _, _ = build_command(repo, "frontend", ["frontend/src/a.test.ts"])

    assert argv[1:] == [
        "run", "--exclude=src/a.test.tsx", "--exclude=src/x/src/a.test.ts", "src/a.test.ts",
    ]


# CI installs bwrap, so there a missing bwrap fails the test instead of skipping it.
needs_bwrap = pytest.mark.skipif(
    shutil.which("bwrap") is None and not os.environ.get("CI"), reason="bubblewrap not installed"
)


@needs_bwrap
def test_sandbox_hides_secret_files_home_and_production_code(
    repo: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch
) -> None:
    home = tmp_path_factory.mktemp("home")
    (home / ".aws").mkdir()
    (home / ".aws/credentials").write_text("aws-secret")
    monkeypatch.setenv("HOME", str(home))
    (repo / ".env").write_text("SECRET=1\n")
    (repo / ".git").mkdir()
    (repo / ".git/config").write_text("token")
    (repo / "backend/app").mkdir()
    (repo / "backend/tests/test_leak.py").write_text(
        "import pathlib, pytest\n"
        f"ROOT = pathlib.Path({str(repo)!r})\n"
        f"HOME = pathlib.Path({str(home)!r})\n"
        "def test_leak():\n"
        "    for secret in (ROOT / '.env', ROOT / '.git/config', HOME / '.aws/credentials'):\n"
        "        with pytest.raises(OSError):\n"
        "            secret.read_text()\n"
        "    with pytest.raises(OSError):\n"
        "        (ROOT / 'backend/app/evil.py').write_text('x')\n"
    )

    result = run_tests(repo, "backend", ["backend/tests/test_leak.py"])

    assert result.passed, result.output
    assert not (repo / "backend/app/evil.py").exists()


def test_missing_bwrap_refuses_to_run(repo: Path, monkeypatch) -> None:
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)

    result = run_tests(repo, "backend", ["backend/tests/test_ok.py"])

    assert result.exit_code == 126 and "bubblewrap" in result.output


def test_sandbox_can_be_disabled_inside_an_isolated_container(repo: Path, monkeypatch) -> None:
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)
    monkeypatch.setenv(sandbox.UNSANDBOXED_ENV, "1")

    assert run_tests(repo, "backend", ["backend/tests/test_ok.py"]).passed


def test_frontend_run_passes_only_when_tests_and_typecheck_pass(repo: Path, monkeypatch) -> None:
    results = {"vitest": (0, "1 passed"), "tsc": (2, "src/a.test.ts(1,7): error TS2322")}
    calls = []

    def fake_execute(argv, repo_root, cwd):
        tool = Path(argv[0]).name
        calls.append(tool)
        return results[tool]

    monkeypatch.setattr(runner, "_execute", fake_execute)

    failed = run_tests(repo, "frontend", ["frontend/src/a.test.ts"])
    results["tsc"] = (0, "")
    passed = run_tests(repo, "frontend", ["frontend/src/a.test.ts"])

    assert calls == ["vitest", "tsc", "vitest", "tsc"]
    assert not failed.passed and failed.exit_code == 2 and "error TS2322" in failed.output
    assert passed.passed and "No type errors." in passed.output


def test_failing_vitest_keeps_its_exit_code_over_typecheck(repo: Path, monkeypatch) -> None:
    monkeypatch.setattr(runner, "_execute", lambda argv, *_: (1, "") if "vitest" in argv[0] else (2, ""))

    assert run_tests(repo, "frontend", ["frontend/src/a.test.ts"]).exit_code == 1


def test_backend_run_has_no_typecheck(repo: Path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(runner, "_execute", lambda argv, *_: calls.append(argv) or (0, ""))

    run_tests(repo, "backend", ["backend/tests/test_ok.py"])

    assert len(calls) == 1
