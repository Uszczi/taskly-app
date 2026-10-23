from datetime import date

from app.features.todos.schemas import Priority, Todo
from app.features.todos.stats import compute_stats

TODAY = date(2026, 10, 23)


def make_todo(todo_values, **overrides):
    return Todo.model_validate({**todo_values, **overrides})


def test_empty_task_list_reports_zero_counts_and_zero_completion_rate():
    stats = compute_stats([], TODAY)
    assert stats.model_dump() == {
        "total": 0,
        "completed": 0,
        "active": 0,
        "overdue": 0,
        "due_today": 0,
        "active_by_priority": {Priority.low: 0, Priority.medium: 0, Priority.high: 0},
        "completion_rate": 0.0,
    }


def test_completed_tasks_are_counted_apart_from_active_ones(todo_values):
    todos = [
        make_todo(todo_values, id=1, completed=True),
        make_todo(todo_values, id=2, completed=False),
        make_todo(todo_values, id=3, completed=False),
    ]
    stats = compute_stats(todos, TODAY)
    assert (stats.total, stats.completed, stats.active) == (3, 1, 2)


def test_overdue_counts_only_active_tasks_due_before_today(todo_values):
    todos = [
        make_todo(todo_values, id=1, due_date=date(2026, 10, 22), completed=False),
        make_todo(todo_values, id=2, due_date=date(2026, 10, 1), completed=True),
        make_todo(todo_values, id=3, due_date=date(2026, 10, 23), completed=False),
        make_todo(todo_values, id=4, due_date=date(2026, 11, 1), completed=False),
        make_todo(todo_values, id=5, due_date=None, completed=False),
    ]
    assert compute_stats(todos, TODAY).overdue == 1


def test_due_today_counts_only_active_tasks_due_on_today(todo_values):
    todos = [
        make_todo(todo_values, id=1, due_date=date(2026, 10, 23), completed=False),
        make_todo(todo_values, id=2, due_date=date(2026, 10, 23), completed=True),
        make_todo(todo_values, id=3, due_date=date(2026, 10, 22), completed=False),
        make_todo(todo_values, id=4, due_date=None, completed=False),
    ]
    assert compute_stats(todos, TODAY).due_today == 1


def test_active_by_priority_lists_every_priority_and_skips_completed_tasks(todo_values):
    todos = [
        make_todo(todo_values, id=1, priority="high", completed=False),
        make_todo(todo_values, id=2, priority="high", completed=False),
        make_todo(todo_values, id=3, priority="low", completed=False),
        make_todo(todo_values, id=4, priority="medium", completed=True),
    ]
    stats = compute_stats(todos, TODAY)
    assert stats.active_by_priority == {Priority.low: 1, Priority.medium: 0, Priority.high: 2}


def test_completion_rate_is_rounded_to_two_decimals(todo_values):
    todos = [
        make_todo(todo_values, id=1, completed=True),
        make_todo(todo_values, id=2, completed=False),
        make_todo(todo_values, id=3, completed=False),
    ]
    assert compute_stats(todos, TODAY).completion_rate == 0.33


def test_completion_rate_is_one_when_every_task_is_completed(todo_values):
    todos = [make_todo(todo_values, id=1, completed=True)]
    assert compute_stats(todos, TODAY).completion_rate == 1.0
