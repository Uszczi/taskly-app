"""Agent tests use scripted models: no network, no API key."""

import json
from collections.abc import AsyncIterator
from pathlib import Path

from pydantic_ai.messages import (
    LoadCapabilityReturnPart,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel

from taskly_test_agent.agent import Deps, FileDecision, Report, agent
from taskly_test_agent.verbose import print_tool_events


def scripted(*steps: list[ToolCallPart]) -> FunctionModel:
    """A fake LLM that returns the given tool calls, one response per turn."""
    turns = iter(steps)

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=next(turns))

    # Used when the run streams, e.g. with an `event_stream_handler`.
    async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[DeltaToolCalls]:
        for i, call in enumerate(next(turns)):
            yield {i: DeltaToolCall(name=call.tool_name, json_args=json.dumps(call.args))}

    return FunctionModel(respond, stream_function=stream)


def output(**args) -> ToolCallPart:
    """Call PydanticAI's built-in output tool, which ends the run with a `Report`."""
    return ToolCallPart("final_result", args)


def test_agent_reads_files_and_returns_report(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    model = scripted(
        [ToolCallPart("list_dir", {"path": "."})],
        [ToolCallPart("read_file", {"path": "a.py"})],
        [output(summary="done", decisions=[{"path": "a.py", "action": "skip", "reason": "constant"}])],
    )

    result = agent.run_sync("inspect", model=model, deps=Deps(repo_root=tmp_path))

    assert result.output == Report(
        summary="done", decisions=[FileDecision(path="a.py", action="skip", reason="constant")]
    )
    returns = [p for m in result.all_messages() for p in m.parts if isinstance(p, ToolReturnPart)]
    assert [r.content for r in returns[:2]] == [["a.py"], "x = 1\n"]


def test_path_escape_is_sent_back_to_model_as_retry(tmp_path: Path) -> None:
    model = scripted(
        [ToolCallPart("read_file", {"path": "../../etc/passwd"})],
        [output(summary="gave up")],
    )

    result = agent.run_sync("inspect", model=model, deps=Deps(repo_root=tmp_path))

    retries = [p for m in result.all_messages() for p in m.parts if isinstance(p, RetryPromptPart)]
    assert len(retries) == 1
    assert "outside the repository" in str(retries[0].content)


def test_verbose_handler_traces_calls_results_and_retries(tmp_path: Path, capsys) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    model = scripted(
        [ToolCallPart("read_file", {"path":"../nope"})],
        [ToolCallPart("read_file", {"path": "a.py"})],
        [output(summary="done")],
    )

    agent.run_sync(
        "inspect", model=model, deps=Deps(repo_root=tmp_path), event_stream_handler=print_tool_events
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        '→ read_file({"path":"../nope"})',
        "✗ read_file: '../nope' is outside the repository",
        '→ read_file({"path":"a.py"})',
        "← read_file: x = 1\\n",
    ]


def test_skill_body_is_only_sent_after_load_capability(tmp_path: Path) -> None:
    model = scripted(
        [ToolCallPart("load_capability", {"id": "test-scope"})],
        [output(summary="done", skills_used=["test-scope"])],
    )

    result = agent.run_sync("plan tests", model=model, deps=Deps(repo_root=tmp_path))

    first_request = result.all_messages()[0]
    assert isinstance(first_request, ModelRequest)
    assert "- test-scope: Decide which changed" in (first_request.instructions or "")
    assert "Deciding what to test" not in str(first_request)
    loaded = [
        p for m in result.all_messages() for p in m.parts if isinstance(p, LoadCapabilityReturnPart)
    ]
    assert len(loaded) == 1
    assert "Deciding what to test" in str(loaded[0].content)
    assert result.output.skills_used == ["test-scope"]


def test_write_test_file_writes_and_records_test_files(tmp_path: Path) -> None:
    model = scripted(
        [ToolCallPart("write_test_file", {"path": "backend/tests/api/test_x.py", "content": "def test_x():\n    pass\n"})],
        [output(summary="done")],
    )
    deps = Deps(repo_root=tmp_path)

    agent.run_sync("write", model=model, deps=deps)

    assert (tmp_path / "backend/tests/api/test_x.py").read_text().startswith("def test_x")
    assert deps.written == ["backend/tests/api/__init__.py", "backend/tests/api/test_x.py"]


def test_write_test_file_refuses_production_code(tmp_path: Path) -> None:
    model = scripted(
        [ToolCallPart("write_test_file", {"path": "backend/app/main.py", "content": "x"})],
        [output(summary="gave up")],
    )
    deps = Deps(repo_root=tmp_path)

    result = agent.run_sync("write", model=model, deps=deps)

    retries = [p for m in result.all_messages() for p in m.parts if isinstance(p, RetryPromptPart)]
    assert "production code is off limits" in str(retries[0].content)
    assert not (tmp_path / "backend/app/main.py").exists()
    assert deps.written == []


def test_read_file_refuses_env_files(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=1\n")
    model = scripted(
        [ToolCallPart("read_file", {"path": ".env"})],
        [output(summary="gave up")],
    )

    result = agent.run_sync("read", model=model, deps=Deps(repo_root=tmp_path))

    retries = [p for m in result.all_messages() for p in m.parts if isinstance(p, RetryPromptPart)]
    assert "may contain secrets" in str(retries[0].content)
    assert "SECRET=1" not in str(result.all_messages())


def test_write_test_file_adds_missing_package_init_files(tmp_path: Path) -> None:
    (tmp_path / "backend/tests").mkdir(parents=True)
    (tmp_path / "backend/tests/__init__.py").touch()
    model = scripted(
        [ToolCallPart("write_test_file", {"path": "backend/tests/features/users/test_router.py", "content": "x = 1\n"})],
        [output(summary="done")],
    )
    deps = Deps(repo_root=tmp_path)

    agent.run_sync("write", model=model, deps=deps)

    assert deps.written == [
        "backend/tests/features/users/__init__.py",
        "backend/tests/features/__init__.py",
        "backend/tests/features/users/test_router.py",
    ]
    assert (tmp_path / "backend/tests/features/__init__.py").exists()
