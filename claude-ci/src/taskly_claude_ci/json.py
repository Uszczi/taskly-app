from pathlib import Path

from pydantic import BaseModel, ValidationError


def read_json[T: BaseModel](path: Path | None, model: type[T]) -> T | None:
    try:
        return model.model_validate_json(path.read_text()) if path else None
    except (OSError, ValidationError):
        return None


def write_json(path: Path, data: BaseModel) -> str:
    text = data.model_dump_json(indent=2)
    path.write_text(text)
    return text
