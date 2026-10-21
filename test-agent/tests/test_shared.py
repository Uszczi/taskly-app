from taskly_test_agent.agent import Report
from taskly_test_agent.shared import INSTRUCTIONS, REPORT_SCHEMA, SKIP_RULES


def _normalize(schema: dict, defs: dict) -> dict:
    """Pydantic's schema in the shared file's shape: refs inlined, no titles or defaults."""
    if "$ref" in schema:
        schema = defs[schema["$ref"].rsplit("/", 1)[-1]] | {k: v for k, v in schema.items() if k != "$ref"}
    out = {}
    for key, value in schema.items():
        if key in ("title", "default", "$defs", "required"):
            continue
        if key == "type" and "enum" in schema:
            continue  # the shared schema states only the enum
        if key == "properties":
            value = {name: _normalize(prop, defs) for name, prop in value.items()}
        elif key == "items":
            value = _normalize(value, defs)
        out[key] = value
    return out


def _without_required(schema: dict) -> dict:
    out = {k: v for k, v in schema.items() if k != "required"}
    if "properties" in out:
        out["properties"] = {name: _without_required(prop) for name, prop in out["properties"].items()}
    if "items" in out:
        out["items"] = _without_required(out["items"])
    return out


def test_report_matches_the_shared_schema() -> None:
    # Claude Code gets the shared file as --json-schema; PydanticAI validates with Report.
    # `required` differs on purpose: Report has defaults, Claude must fill every field.
    pydantic_schema = Report.model_json_schema()
    assert _normalize(pydantic_schema, pydantic_schema.get("$defs", {})) == _without_required(REPORT_SCHEMA)


def test_shared_instructions_and_skip_rules_are_loaded() -> None:
    assert INSTRUCTIONS.startswith("You are a test engineer for the Taskly repository")
    assert "backend/app/main.py" in SKIP_RULES["backend"]["skip_paths"]
