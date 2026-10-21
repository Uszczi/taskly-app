from unittest.mock import create_autospec

from sqlalchemy.orm import Session

from app.features.todos.repository import TodoRepository


def make_repository_mock():
    """Return a fresh, interface-checked mock shared by API tests."""
    repository = create_autospec(TodoRepository, instance=True)
    # autospec only knows class attributes; `session` is set in __init__.
    repository.session = create_autospec(Session, instance=True)
    repository.list.return_value = []
    return repository
