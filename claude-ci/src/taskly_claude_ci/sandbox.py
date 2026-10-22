import os
import subprocess
from pathlib import Path

TIMEOUT_SECONDS = 600


def sandboxed(repo: Path, cwd: Path, argv: list[str]) -> list[str]:
    env = [
        f"PATH={os.environ.get('PATH', '/usr/bin:/bin')}",
        f"HOME={os.environ.get('HOME', '/tmp')}",
        "NO_COLOR=1",
        "CI=1",
        "PYTHONDONTWRITEBYTECODE=1",
    ]
    return [
        "env",
        "-i",
        *env,
        "bwrap",
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(repo),
        str(repo),
        "--unshare-all",
        "--die-with-parent",
        "--chdir",
        str(cwd),
        "--",
        *argv,
    ]


def run(repo: Path, cwd: Path, argv: list[str], log: Path) -> int:
    try:
        proc = subprocess.run(
            sandboxed(repo, cwd, argv),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        log.write_text(f"Timed out after {TIMEOUT_SECONDS}s\n")
        return 124
    log.write_text(proc.stdout + proc.stderr)
    return proc.returncode
