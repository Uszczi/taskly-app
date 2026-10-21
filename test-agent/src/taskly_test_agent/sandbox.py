"""Run model-written tests inside a bubblewrap (bwrap) sandbox.

Filtering the environment is not enough: a test can open files and print them,
and the output goes back to the model. Inside the sandbox the test sees:
- the filesystem read-only, with $HOME, /tmp and /run replaced by empty tmpfs
  (no ~/.aws, ~/.ssh, agent sockets); the repo and the toolchain stay visible,
- `.git` hidden (CI checkouts keep a token in .git/config) and `.env*` files
  in the repo unreadable,
- no network and its own PID namespace, so `/proc/<agent pid>/environ` and
  exfiltration over the network are out of reach,
- the repo read-only, so test code cannot rewrite production code either.

Set TASKLY_AGENT_UNSANDBOXED=1 only when the agent itself already runs in a
throwaway container that holds no secrets.
"""

import json
import os
import shutil
import subprocess
from functools import cache
from pathlib import Path

from .paths import is_secret

UNSANDBOXED_ENV = "TASKLY_AGENT_UNSANDBOXED"
# Caches vite writes on startup; each gets an empty tmpfs.
_FRONTEND_WRITABLE = ("frontend/node_modules/.vite", "frontend/node_modules/.vite-temp")
_WALK_SKIP = {".git", "node_modules", ".venv", "__pycache__"}


class SandboxUnavailable(RuntimeError):
    pass


def sandbox_enabled() -> bool:
    return os.environ.get(UNSANDBOXED_ENV) != "1"


def wrap(argv: list[str], repo_root: Path, cwd: Path) -> list[str]:
    """`argv` wrapped in bwrap. Raises SandboxUnavailable when bwrap is missing."""
    bwrap = shutil.which("bwrap")
    if bwrap is None:
        raise SandboxUnavailable(
            "bubblewrap (bwrap) is not installed, so tests cannot run safely; "
            f"install it, or set {UNSANDBOXED_ENV}=1 inside an isolated container"
        )
    repo_root = repo_root.resolve()
    home = Path.home().resolve()
    args = [
        bwrap, "--die-with-parent", "--new-session", "--unshare-all",
        "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
        "--tmpfs", "/tmp", "--tmpfs", "/run", "--tmpfs", str(home),
    ]
    hidden = (home, Path("/tmp"), Path("/run"))
    dirs, executables = _toolchain(argv[0])
    # Mounted after the tmpfs layers, so they reappear when they live under one of them.
    for path in (*dirs, repo_root):
        args += ["--ro-bind", str(path), str(path)]
    # uv and pyenv reach the interpreter through symlinks (cpython-3.12 -> cpython-3.12.13).
    for executable in (argv[0], *executables):
        for link, target in _symlink_hops(executable):
            if any(link.is_relative_to(h) for h in hidden):
                args += ["--symlink", target, str(link)]
    git = repo_root / ".git"
    if git.is_dir():
        args += ["--tmpfs", str(git)]
    elif git.exists():  # worktree: .git is a file pointing elsewhere
        args += ["--ro-bind", "/dev/null", str(git)]
    for secret in _secret_files(repo_root):
        args += ["--ro-bind", "/dev/null", str(secret)]
    if (repo_root / "frontend/node_modules").is_dir():
        for rel in _FRONTEND_WRITABLE:
            (repo_root / rel).mkdir(exist_ok=True)
            args += ["--tmpfs", str(repo_root / rel)]
    return [*args, "--chdir", str(cwd), "--", *argv]


def _secret_files(repo_root: Path) -> list[Path]:
    found = []
    for directory, subdirs, files in os.walk(repo_root):
        subdirs[:] = [d for d in subdirs if d not in _WALK_SKIP]
        found += [
            Path(directory, name) for name in files if is_secret(repo_root, Path(directory, name))
        ]
    return found


def _symlink_hops(path: str) -> list[tuple[Path, str]]:
    """(link, target) for every symlink followed while resolving `path`."""
    hops: list[tuple[Path, str]] = []
    parts = list(Path(os.path.abspath(path)).parts[1:])
    current = Path("/")
    while parts and len(hops) < 40:
        current = current / parts.pop(0)
        if current.is_symlink():
            target = os.readlink(current)
            hops.append((current, target))
            parts = list(Path(os.path.normpath(current.parent / target)).parts[1:]) + parts
            current = Path("/")
    return hops


def _toolchain(executable: str) -> tuple[list[Path], list[str]]:
    """(directories, executables) the test runner needs that may live under $HOME (uv, pyenv, nvm)."""
    if executable.endswith("vitest"):
        node = shutil.which("node")
        return ([Path(node).resolve().parent.parent], [node]) if node else ([], [])
    return _python_toolchain(executable)


@cache
def _python_toolchain(python: str) -> tuple[list[Path], list[str]]:
    # Asks the interpreter itself, so venvs and wrapper scripts resolve correctly.
    out = subprocess.run(
        [python, "-c", "import json, sys; print(json.dumps([sys.prefix, sys.base_prefix, sys.executable]))"],
        capture_output=True, text=True, timeout=30,
    )
    if out.returncode != 0:
        return [], []
    prefix, base_prefix, real_executable = json.loads(out.stdout)
    return [Path(prefix).resolve(), Path(base_prefix).resolve()], [real_executable]
