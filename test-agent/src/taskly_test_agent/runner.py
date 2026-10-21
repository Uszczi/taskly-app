"""Run the backend or frontend test suite with a fixed command line.

Test code is written by the model, so running it is running untrusted code:
- the command is fixed (no shell, no model-chosen flags),
- only repository test files may be passed as arguments,
- the child process gets a minimal environment, so API keys and tokens in the
  agent's environment are never visible to the tests,
- it runs in a bwrap sandbox (see `sandbox`), so it cannot read secret files
  from disk either,
- runs are time-limited and their output is truncated before reaching the model.
"""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .paths import PathNotAllowed, is_test_path, resolve_in_repo
from .sandbox import SandboxUnavailable, sandbox_enabled, wrap

Target = Literal["backend", "frontend"]

TIMEOUT_SECONDS = 300
MAX_OUTPUT_CHARS = 8_000
_ENV_ALLOWLIST = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "CI")
# vitest's default `include`: every file it would pick up as a test.
_VITEST_FILE = re.compile(r"\.(test|spec)\.[cm]?[jt]sx?$")


@dataclass(frozen=True)
class TestRun:
    __test__ = False  # not a pytest test class

    target: Target
    paths: tuple[str, ...]
    exit_code: int | None  # None when the run timed out
    output: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def backend_python(repo_root: Path) -> str:
    venv = repo_root / "backend/.venv/bin/python"
    return os.environ.get("BACKEND_PYTHON") or (str(venv) if venv.exists() else "python3")


def build_command(
    repo_root: Path, target: Target, paths: list[str]
) -> tuple[list[str], Path, tuple[str, ...]]:
    """Validate `paths` and return (argv, cwd, repo-relative files). Raises PathNotAllowed."""
    # Absolute, so the interpreter and binary paths stay valid in the child's cwd.
    repo_root = repo_root.resolve()
    files = []
    for raw in paths:
        resolved = resolve_in_repo(repo_root, raw)
        prefix = "backend/tests/" if target == "backend" else "frontend/src/"
        rel = resolved.relative_to(repo_root).as_posix()
        if not rel.startswith(prefix) or not is_test_path(repo_root, resolved):
            raise PathNotAllowed(f"{raw!r} is not a {target} test file")
        if not resolved.is_file():
            raise PathNotAllowed(f"{raw!r} does not exist")
        files.append(rel)

    if target == "backend":
        # Repo-relative paths; the root pytest.ini adds `backend` to sys.path.
        argv = [backend_python(repo_root), "-m", "pytest", "-q", "-p", "no:cacheprovider", *files]
        return argv, repo_root, tuple(files)
    vitest = repo_root / "frontend/node_modules/.bin/vitest"
    filters = [f.removeprefix("frontend/") for f in files]
    excludes = [f"--exclude={other}" for other in _vitest_extra_matches(repo_root, filters)]
    # Local binary only: `npx` could download and run a package that is not installed.
    argv = [str(vitest), "run", *excludes, *filters]
    return argv, repo_root / "frontend", tuple(files)


def _vitest_extra_matches(repo_root: Path, filters: list[str]) -> list[str]:
    """Other test files vitest would also run: its file filters are substring matches.

    `src/a.test.ts` alone would also run `src/a.test.tsx` and `src/x/src/a.test.ts`.
    """
    frontend = repo_root / "frontend"
    wanted = {f.lower() for f in filters}
    extra = []
    for file in (frontend / "src").rglob("*"):
        rel = file.relative_to(frontend).as_posix()
        if "node_modules" in file.parts or not _VITEST_FILE.search(rel):
            continue
        if rel.lower() not in wanted and any(f in rel.lower() for f in wanted):
            extra.append(rel)
    return sorted(extra)


def _tail(text: str) -> str:
    # Failures and the summary are at the end of pytest/vitest output.
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return "... [truncated]\n" + text[-MAX_OUTPUT_CHARS:]


def typecheck_command(repo_root: Path) -> tuple[list[str], Path]:
    """`tsc --noEmit` over the frontend project, test files included (tsconfig `include`)."""
    frontend = repo_root.resolve() / "frontend"
    return [str(frontend / "node_modules/.bin/tsc"), "--noEmit", "-p", "."], frontend


def _execute(argv: list[str], repo_root: Path, cwd: Path) -> tuple[int | None, str]:
    env = {key: os.environ[key] for key in _ENV_ALLOWLIST if key in os.environ}
    env["NO_COLOR"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"  # the repo is read-only in the sandbox
    try:
        if sandbox_enabled():
            argv = wrap(argv, repo_root, cwd)
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return None, f"Timed out after {TIMEOUT_SECONDS}s"
    except SandboxUnavailable as exc:
        return 126, str(exc)
    except FileNotFoundError as exc:
        return 127, f"Test runner not installed: {exc.filename}"
    return proc.returncode, _tail(proc.stdout + proc.stderr)


def run_tests(repo_root: Path, target: Target, paths: list[str]) -> TestRun:
    """Run the tests; for the frontend, also typecheck, and pass only when both pass."""
    argv, cwd, files = build_command(repo_root, target, paths)
    code, output = _execute(argv, repo_root, cwd)
    if target == "frontend":
        # vitest strips types without checking them, so a test that does not compile can pass.
        tsc_argv, tsc_cwd = typecheck_command(repo_root)
        tsc_code, tsc_output = _execute(tsc_argv, repo_root, tsc_cwd)
        output += f"\n--- tsc --noEmit (exit code {tsc_code}) ---\n{tsc_output or 'No type errors.'}"
        if code == 0:
            code = tsc_code
    return TestRun(target, files, code, output)
