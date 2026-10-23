from datetime import date

import pytest

from app.features.todos.schemas import Todo
from app.features.todos.stats import compute_stats

TODAY = date(2026, 10, 15)


def make_todo(todo_values, **overrides):
    return Todo.model_validate({**todo_values, **overrides})


def test_compute_stats_returns_zeroes_and_zero_rate_for_no_tasks():
    stats = compute_stats([], TODAY)
    assert stats.total == 0
    assert stats.completed == 0
    assert stats.active == 0
    assert stats.overdue == 0
    assert stats.due_today == 0
    assert stats.completion_rate == 0.0
    assert stats.active_by_priority == {"low": 0, "medium": 0, "high": 0}


def test_compute_stats_counts_completed_and_active_tasks(todo_values):
    todos = [
        make_todo(todo_values, id=1, completed=True),
        make_todo(todo_values, id=2, completed=False),
        make_todo(todo_values, id=3, completed=False),
    ]
    stats = compute_stats(todos, TODAY)
    assert stats.total == 3
    assert stats.completed == 1
    assert stats.active == 2
    assert stats.completion_rate == 0.33


def test_compute_stats_rounds_completion_rate_to_two_decimals(todo_values):
    todos = [make_todo(todo_values, id=i, completed=i < 3) for i in range(1, 4)]
    assert compute_stats(todos, TODAY).completion_rate == 0.67


def test_compute_stats_reports_completion_rate_of_one_when_everything_is_done(todo_values):
    todos = [make_todo(todo_values, id=i, completed=True) for i in range(1, 3)]
    stats = compute_stats(todos, TODAY)
    assert stats.completion_rate == 1.0
    assert stats.active == 0


def test_compute_stats_counts_only_active_tasks_due_before_today_as_overdue(todo_values):
    todos = [
        make_todo(todo_values, id=1, due_date=date(2026, 10, 14)),
        make_todo(todo_values, id=2, due_date=date(2026, 10, 15)),
        make_todo(todo_values, id=3, due_date=date(2026, 10, 14), completed=True),
        make_todo(todo_values, id=4, due_date=None),
    ]
    assert compute_stats(todos, TODAY).overdue == 1


def test_compute_stats_counts_only_active_tasks_due_today(todo_values):
    todos = [
        make_todo(todo_values, id=1, due_date=TODAY),
        make_todo(todo_values, id=2, due_date=TODAY, completed=True),
        make_todo(todo_values, id=3, due_date=date(2026, 10, 16)),
    ]
    assert compute_stats(todos, TODAY).due_today == 1


def test_compute_stats_groups_active_tasks_by_priority_and_ignores_completed(todo_values):
    todos = [
        make_todo(todo_values, id=1, priority="high"),
        make_todo(todo_values, id=2, priority="high"),
        make_todo(todo_values, id=3, priority="low"),
        make_todo(todo_values, id=4, priority="high", completed=True),
    ]
    stats = compute_stats(todos, TODAY)
    assert stats.active_by_priority == {"low": 1, "medium": 0, "high": 2}


@pytest.mark.parametrize("today", [date(2026, 10, 14), date(2026, 10, 16)])
def test_compute_stats_depends_on_the_day_it_is_given(todo_values, today):
    todos = [make_todo(todo_values, id=1, due_date=date(2026, 10, 15))]
    stats = compute_stats(todos, today)
    assert stats.overdue == (1 if today > date(2026, 10, 15) else 0)
    assert stats.due_today == 0
