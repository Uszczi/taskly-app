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

`backend/tests/conftest.py` and `backend/tests/mocks.py` are read-only for you.
A fixture they lack goes in the test file, or in a `conftest.py` next to it
(e.g. `backend/tests/core/conftest.py`) when several files in that directory
share it. When the shared files themselves need a change, describe it in the
decision's reason for a maintainer to make.

## Style

- Plain functions named `test_<behavior>`; no test classes.
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

Call `run_tests` with target `backend` and paths from the repository root,
e.g. `backend/tests/features/todos/test_mappers.py`.
