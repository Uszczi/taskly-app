from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_repository
from app.features.todos.router import get_today, router
from app.features.todos.schemas import Todo, TodoCreate


def test_list_returns_tasks_from_repository(client, repository_mock, todo):
    repository_mock.list.return_value = [todo]
    response = client.get("/api/todos")
    assert response.status_code == 200
    assert response.json() == [todo.model_dump(mode="json")]
    repository_mock.list.assert_called_once_with()


def test_create_trims_input_and_returns_created_task(client, repository_mock, todo):
    repository_mock.create.return_value = todo
    response = client.post("/api/todos", json={"title": "  Plan the sprint  ", "priority": "high"})
    assert response.status_code == 201
    assert response.json() == todo.model_dump(mode="json")
    repository_mock.create.assert_called_once_with(
        TodoCreate(title="Plan the sprint", priority="high")
    )


@pytest.mark.parametrize("payload", [
    {"title": "   "},
    {"title": "x" * 121},
    {"title": "Task", "priority": "urgent"},
    {"title": "Task", "due_date": "2026-02-30"},
])
def test_invalid_create_never_calls_repository(client, repository_mock, payload):
    assert client.post("/api/todos", json=payload).status_code == 422
    repository_mock.create.assert_not_called()


@pytest.fixture
def stats_client(repository_mock):
    # Pins "today" so overdue and due-today counts do not depend on the clock.
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_repository] = lambda: repository_mock
    app.dependency_overrides[get_today] = lambda: date(2026, 10, 23)
    with TestClient(app) as client:
        yield client


def test_stats_summarize_tasks_as_of_the_callers_today(stats_client, repository_mock, todo_values):
    overdue = {**todo_values, "id": 1, "due_date": "2026-10-22", "completed": False}
    due_today = {**todo_values, "id": 2, "priority": "medium", "due_date": "2026-10-23"}
    done = {**todo_values, "id": 3, "priority": "low", "completed": True}
    repository_mock.list.return_value = [Todo.model_validate(v) for v in (overdue, due_today, done)]
    response = stats_client.get("/api/todos/stats")
    assert response.status_code == 200
    assert response.json() == {
        "total": 3,
        "completed": 1,
        "active": 2,
        "overdue": 1,
        "due_today": 1,
        "active_by_priority": {"low": 0, "medium": 1, "high": 1},
        "completion_rate": 0.33,
    }


def test_stats_path_is_not_read_as_a_todo_id(stats_client, repository_mock):
    assert stats_client.get("/api/todos/stats").status_code == 200
    repository_mock.get.assert_not_called()


@pytest.mark.parametrize("deleted", [0, 2])
def test_clear_completed_reports_how_many_tasks_were_deleted(client, repository_mock, deleted):
    repository_mock.delete_completed.return_value = deleted
    response = client.delete("/api/todos/completed")
    assert response.status_code == 200
    assert response.json() == {"deleted": deleted}
    repository_mock.delete_completed.assert_called_once_with()
