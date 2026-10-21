from datetime import date

import pytest

from app.features.todos.schemas import Priority, TodoStats
from app.features.todos.stats import compute_stats

TODAY = date(2026, 10, 22)


def test_empty_list_has_zero_counts_and_zero_completion_rate():
    assert compute_stats([], TODAY) == TodoStats(
        total=0,
        completed=0,
        active=0,
        overdue=0,
        due_today=0,
        active_by_priority={Priority.low: 0, Priority.medium: 0, Priority.high: 0},
        completion_rate=0.0,
    )


def test_counts_deadlines_and_priorities_of_active_tasks_only(todo):
    todos = [
        todo.model_copy(update={"id": 1, "due_date": date(2026, 10, 21), "priority": Priority.high}),
        todo.model_copy(update={"id": 2, "due_date": TODAY, "priority": Priority.low}),
        todo.model_copy(update={"id": 3, "due_date": date(2026, 10, 23), "priority": Priority.high}),
        todo.model_copy(update={"id": 4, "due_date": None, "priority": Priority.high}),
        todo.model_copy(update={"id": 5, "due_date": date(2026, 10, 1), "completed": True}),
        todo.model_copy(update={"id": 6, "due_date": TODAY, "completed": True}),
    ]
    stats = compute_stats(todos, TODAY)
    assert stats.total == 6
    assert stats.completed == 2
    assert stats.active == 4
    assert stats.overdue == 1
    assert stats.due_today == 1
    assert stats.active_by_priority == {Priority.low: 1, Priority.medium: 0, Priority.high: 3}


@pytest.mark.parametrize(("completed", "total", "rate"), [(1, 3, 0.33), (2, 3, 0.67), (3, 3, 1.0)])
def test_completion_rate_is_rounded_to_two_decimals(todo, completed, total, rate):
    todos = [
        todo.model_copy(update={"id": index, "completed": index < completed})
        for index in range(total)
    ]
    assert compute_stats(todos, TODAY).completion_rate == rate
