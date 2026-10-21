from datetime import date

from app.features.todos.schemas import TodoStats
from app.features.todos.stats import compute_stats

TODAY = date(2026, 10, 2)


def test_empty_list_reports_zeros_and_zero_completion_rate():
    stats = compute_stats([], TODAY)
    assert stats == TodoStats(
        total=0,
        completed=0,
        active=0,
        overdue=0,
        due_today=0,
        active_by_priority={"low": 0, "medium": 0, "high": 0},
        completion_rate=0.0,
    )


def test_overdue_and_due_today_only_count_active_tasks(todo):
    todos = [
        todo.model_copy(update={"due_date": date(2026, 10, 1)}),  # overdue
        todo.model_copy(update={"due_date": TODAY}),  # due today, not overdue
        todo.model_copy(update={"due_date": date(2026, 10, 3)}),  # future
        todo.model_copy(update={"due_date": None}),
        todo.model_copy(update={"due_date": date(2026, 10, 1), "completed": True}),
        todo.model_copy(update={"due_date": TODAY, "completed": True}),
    ]
    stats = compute_stats(todos, TODAY)
    assert stats.overdue == 1
    assert stats.due_today == 1


def test_counts_completed_and_active_and_groups_active_by_priority(todo):
    todos = [
        todo.model_copy(update={"priority": "high"}),
        todo.model_copy(update={"priority": "high", "completed": True}),
        todo.model_copy(update={"priority": "low"}),
        todo.model_copy(update={"priority": "medium", "completed": True}),
    ]
    stats = compute_stats(todos, TODAY)
    assert (stats.total, stats.completed, stats.active) == (4, 2, 2)
    assert stats.active_by_priority == {"low": 1, "medium": 0, "high": 1}


def test_completion_rate_is_rounded_to_two_decimals(todo):
    todos = [todo.model_copy(update={"completed": True}), todo.model_copy(), todo.model_copy()]
    assert compute_stats(todos, TODAY).completion_rate == 0.33


def test_all_completed_gives_full_completion_rate(todo):
    todos = [todo.model_copy(update={"completed": True})]
    stats = compute_stats(todos, TODAY)
    assert stats.completion_rate == 1
    assert stats.active == 0
