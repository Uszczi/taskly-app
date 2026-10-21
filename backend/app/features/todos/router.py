from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response

from ...api.dependencies import Repository
from .schemas import ClearCompletedResult, Todo, TodoCreate, TodoStats, TodoUpdate
from .stats import compute_stats

router = APIRouter(prefix="/api/todos", tags=["todos"])
TodoId = Annotated[int, Path(gt=0)]


def get_today() -> date:
    return date.today()


Today = Annotated[date, Depends(get_today)]


@router.get("", response_model=list[Todo])
def list_todos(repo: Repository):
    return repo.list()


@router.post("", response_model=Todo, status_code=201)
def create_todo(payload: TodoCreate, repo: Repository):
    return repo.create(payload)


# Fixed paths go before /{todo_id}, which would otherwise reject them as invalid ids.
@router.get("/stats", response_model=TodoStats)
def get_stats(repo: Repository, today: Today):
    return compute_stats(repo.list(), today)


@router.delete("/completed", response_model=ClearCompletedResult)
def clear_completed(repo: Repository):
    return ClearCompletedResult(deleted=repo.delete_completed())


@router.get("/{todo_id}", response_model=Todo)
def get_todo(todo_id: TodoId, repo: Repository):
    todo = repo.get(todo_id)
    if todo is None:
        raise HTTPException(404, "Task not found.")
    return todo


@router.patch("/{todo_id}", response_model=Todo)
def update_todo(todo_id: TodoId, payload: TodoUpdate, repo: Repository):
    todo = repo.update(todo_id, payload)
    if todo is None:
        raise HTTPException(404, "Task not found.")
    return todo


@router.delete("/{todo_id}", status_code=204)
def delete_todo(todo_id: TodoId, repo: Repository):
    if not repo.delete(todo_id):
        raise HTTPException(404, "Task not found.")
    return Response(status_code=204)
