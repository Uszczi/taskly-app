from datetime import date

import pytest

from app.features.todos.router import get_today
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


def test_stats_are_computed_from_listed_tasks_as_of_today(client, repository_mock, todo_values):
    overdue = Todo.model_validate(dict(todo_values, due_date=date(2026, 10, 9)))
    done = Todo.model_validate(dict(todo_values, id=8, completed=True))
    repository_mock.list.return_value = [overdue, done]
    client.app.dependency_overrides[get_today] = lambda: date(2026, 10, 10)
    response = client.get("/api/todos/stats")
    assert response.status_code == 200
    body = response.json()
    assert (body["total"], body["completed"], body["active"], body["overdue"]) == (2, 1, 1, 1)
    assert body["active_by_priority"] == {"low": 0, "medium": 0, "high": 1}
    assert body["completion_rate"] == 0.5


def test_clear_completed_returns_deleted_count(client, repository_mock):
    repository_mock.delete_completed.return_value = 2
    response = client.delete("/api/todos/completed")
    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    repository_mock.delete_completed.assert_called_once_with()
    repository_mock.get.assert_not_called()
