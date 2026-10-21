from pathlib import Path

import pytest

from taskly_test_agent.paths import PathNotAllowed, is_test_path, resolve_in_repo


def test_resolves_path_inside_repo(tmp_path: Path) -> None:
    assert resolve_in_repo(tmp_path, "backend/app.py") == tmp_path.resolve() / "backend/app.py"


@pytest.mark.parametrize("bad", ["../secret", "/etc/passwd", "backend/../../x"])
def test_rejects_paths_escaping_repo(tmp_path: Path, bad: str) -> None:
    with pytest.raises(PathNotAllowed):
        resolve_in_repo(tmp_path, bad)


def test_rejects_symlink_pointing_outside(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "link").symlink_to(tmp_path)
    with pytest.raises(PathNotAllowed):
        resolve_in_repo(repo, "link/outside.txt")


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("backend/tests/features/test_x.py", True),
        ("frontend/src/hooks/useNotice.test.ts", True),
        ("frontend/src/App.test.tsx", True),
        ("backend/app/factory.py", False),
        ("frontend/src/App.tsx", False),
        ("frontend/vite.config.ts", False),
        (".github/workflows/ci.yml", False),
        ("backend/tests/conftest.py", False),
        ("backend/tests/mocks.py", False),
        ("backend/tests/features/todos/conftest.py", True),
        ("frontend/src/test/setup.ts", False),
    ],
)
def test_is_test_path(tmp_path: Path, rel: str, expected: bool) -> None:
    assert is_test_path(tmp_path, tmp_path / rel) is expected
