from collections import Counter
from datetime import date

from .schemas import Priority, Todo, TodoStats


def compute_stats(todos: list[Todo], today: date) -> TodoStats:
    """Summarize the task list as of `today` (the caller's local date)."""
    active = [todo for todo in todos if not todo.completed]
    by_priority = Counter(todo.priority for todo in active)
    total = len(todos)
    completed = total - len(active)
    return TodoStats(
        total=total,
        completed=completed,
        active=len(active),
        overdue=sum(1 for todo in active if todo.due_date is not None and todo.due_date < today),
        due_today=sum(1 for todo in active if todo.due_date == today),
        active_by_priority={priority: by_priority.get(priority, 0) for priority in Priority},
        completion_rate=round(completed / total, 2) if total else 0.0,
    )
