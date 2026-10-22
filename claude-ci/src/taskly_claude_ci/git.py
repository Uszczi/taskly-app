import re
import subprocess
from pathlib import Path

# A git ref or SHA from the CI event; never something git could read as an option.
_SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/~^-]*$")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    ).stdout


def _since(base: str) -> str:
    if not _SAFE_REF.match(base):
        raise ValueError(f"invalid git ref: {base!r}")
    return f"{base}...HEAD"


def changed_files(repo: Path, base: str, *paths: str) -> list[str]:
    names = git(
        repo,
        "diff",
        "--name-only",
        "-z",
        "--diff-filter=AMR",
        _since(base),
        "--",
        *paths,
    )
    return [p for p in names.split("\0") if p]


def file_diff(repo: Path, base: str, path: str) -> str:
    return git(repo, "diff", "--no-color", "--no-ext-diff", _since(base), "--", path)


def status_entries(repo: Path) -> list[str]:
    return git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").split(
        "\0"
    )
