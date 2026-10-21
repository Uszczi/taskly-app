"""Path guards shared by every tool that touches the filesystem.

The agent receives paths from the model, so they are untrusted input.
"""

from pathlib import Path


class PathNotAllowed(ValueError):
    pass


def resolve_in_repo(root: Path, relative: str) -> Path:
    """Resolve `relative` against `root`, rejecting anything that escapes it.

    `resolve()` follows symlinks, so a link pointing outside the repo is
    rejected as well as `../` traversal and absolute paths.
    """
    root = root.resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise PathNotAllowed(f"{relative!r} is outside the repository")
    return candidate


# Shared test infrastructure: changing it could silently alter every other test.
PROTECTED_TEST_FILES = frozenset({"backend/tests/conftest.py", "backend/tests/mocks.py"})


def is_test_path(root: Path, path: Path) -> bool:
    """True for files the agent is allowed to create or modify."""
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    if rel in PROTECTED_TEST_FILES:
        return False
    if rel.startswith("backend/tests/") and rel.endswith(".py"):
        return True
    if rel.startswith("frontend/src/") and rel.endswith((".test.ts", ".test.tsx")):
        return True
    return False


def is_secret(root: Path, file: Path) -> bool:
    """`.git` and `.env*` files: never shown to the model, hidden from test runs."""
    rel = file.relative_to(root.resolve())
    if rel.parts and rel.parts[0] == ".git":
        return True
    return file.name.startswith(".env") and file.name != ".env.example"
