---
name: backend-unit-tests
description: Conventions for writing pytest unit tests for the Taskly FastAPI backend (backend/app). Load before writing or updating any Python test.
---

# Backend unit tests (pytest + FastAPI)

## Layout

- Source lives in `backend/app/`, tests in `backend/tests/`, mirroring the path:
  `backend/app/features/todos/mappers.py` → `backend/tests/features/todos/test_mappers.py`.
- Every test package directory has an empty `__init__.py`; add one when you
  create a new test directory.
- Imports are absolute from the backend root: `from app.features.todos.schemas import Todo`,
  `from tests.mocks import make_repository_mock`.

## Shared fixtures (`backend/tests/conftest.py`)

Reuse these instead of redefining them:

- `repository_mock`: `create_autospec(TodoRepository, instance=True)`, so calls
  are checked against the real interface. `list` returns `[]` by default, and
  `session` is an autospec of SQLAlchemy's `Session` (e.g. for the health endpoint).
- `client`: a `TestClient` for a bare `FastAPI()` with only the todos router
  mounted and `get_repository` overridden with `repository_mock`.
  It does **not** include the app factory, lifespan, or health router: to test
  those, build the app with `app.factory` in the test itself.
- `todo_values`, `todo` (a validated `Todo`), `model_factory` (builds `TodoRecord`).

A fixture only one test file needs goes in that file; one several files in a
directory share goes in a `conftest.py` next to them (e.g.
`backend/tests/core/conftest.py`). Change `backend/tests/conftest.py` or
`backend/tests/mocks.py` only when every test would benefit, and keep the
existing fixtures working: every backend test depends on them.

## Style

- Plain functions named `test_<behavior>`; no test classes. The name is the
  behavior, not the function under test: `test_completion_rate_is_rounded_to_two_decimals`,
  not `test_compute_stats_rounds_completion_rate`.
- Parametrize input variations with `@pytest.mark.parametrize`.
- Assert both the result and the interaction, e.g. status code, JSON body, and
  `repository_mock.create.assert_called_once_with(...)` or `assert_not_called()`.
- Validation errors: `with pytest.raises(ValidationError, match="...")`.
- Use fixed `datetime(..., tzinfo=timezone.utc)` values for time.
- Use `tmp_path` for anything touching the filesystem or SQLite.

## Example

```python
@pytest.mark.parametrize("payload", [{"title": "   "}, {"title": "x" * 121}])
def test_invalid_create_never_calls_repository(client, repository_mock, payload):
    assert client.post("/api/todos", json=payload).status_code == 422
    repository_mock.create.assert_not_called()
```

## Running

From the repository root, with test paths relative to it; the whole suite is
`backend/tests`:

```bash
backend/.venv/bin/python -m pytest -q -p no:cacheprovider backend/tests/features/todos/test_mappers.py
backend/.venv/bin/python -m pytest -q -p no:cacheprovider backend/tests
```
