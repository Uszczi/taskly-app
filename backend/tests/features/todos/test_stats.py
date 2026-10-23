from datetime import date

import pytest

from app.features.todos.schemas import Priority, Todo
from app.features.todos.stats import compute_stats

TODAY = date(2026, 10, 10)


@pytest.fixture
def make(todo_values):
    return lambda **overrides: Todo.model_validate(dict(todo_values, **overrides))


def test_empty_list_has_zero_completion_rate_and_all_priorities():
    stats = compute_stats([], TODAY)
    assert stats.total == 0
    assert stats.completion_rate == 0.0
    assert stats.active_by_priority == {Priority.low: 0, Priority.medium: 0, Priority.high: 0}


def test_overdue_and_due_today_count_only_active_tasks(make):
    todos = [
        make(id=1, due_date=date(2026, 10, 9)),
        make(id=2, due_date=TODAY),
        make(id=3, due_date=date(2026, 10, 11)),
        make(id=4, due_date=None),
        make(id=5, due_date=date(2026, 10, 1), completed=True),
        make(id=6, due_date=TODAY, completed=True),
    ]
    stats = compute_stats(todos, TODAY)
    assert (stats.overdue, stats.due_today) == (1, 1)
    assert (stats.total, stats.completed, stats.active) == (6, 2, 4)


def test_priority_breakdown_ignores_completed_tasks(make):
    todos = [
        make(id=1, priority="high"),
        make(id=2, priority="high"),
        make(id=3, priority="low"),
        make(id=4, priority="medium", completed=True),
    ]
    assert compute_stats(todos, TODAY).active_by_priority == {
        Priority.low: 1,
        Priority.medium: 0,
        Priority.high: 2,
    }


def test_completion_rate_is_rounded_to_two_decimals(make):
    todos = [make(id=1, completed=True), make(id=2), make(id=3)]
    assert compute_stats(todos, TODAY).completion_rate == 0.33
