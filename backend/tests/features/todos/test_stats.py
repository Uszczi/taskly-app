from datetime import date

from app.features.todos.schemas import Todo
from app.features.todos.stats import compute_stats

TODAY = date(2026, 10, 10)


def test_empty_list_gives_zero_stats(todo_values):
    stats = compute_stats([], TODAY)
    assert stats.total == 0
    assert stats.completion_rate == 0.0
    assert stats.active_by_priority == {"low": 0, "medium": 0, "high": 0}


def test_counts_overdue_and_due_today_only_for_active_tasks(todo_values):
    def make(**overrides):
        return Todo.model_validate({**todo_values, **overrides})

    todos = [
        make(id=1, due_date="2026-10-09"),
        make(id=2, due_date="2026-10-10", priority="low"),
        make(id=3, due_date="2026-10-11", priority="medium"),
        make(id=4, due_date="2026-10-01", completed=True),
        make(id=5, due_date="2026-10-10", completed=True),
        make(id=6, due_date=None),
    ]
    stats = compute_stats(todos, TODAY)
    assert (stats.total, stats.completed, stats.active) == (6, 2, 4)
    assert stats.overdue == 1
    assert stats.due_today == 1
    assert stats.active_by_priority == {"low": 1, "medium": 1, "high": 2}


def test_completion_rate_is_rounded_to_two_decimals(todo_values):
    todos = [
        Todo.model_validate({**todo_values, "id": i, "completed": i == 1}) for i in range(1, 4)
    ]
    assert compute_stats(todos, TODAY).completion_rate == 0.33
