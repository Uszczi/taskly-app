"""Live trace of tool calls, printed to stderr so stdout stays pure JSON."""

import sys
from collections.abc import AsyncIterable
from typing import Any

from pydantic_ai import (
    AgentStreamEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    RetryPromptPart,
    RunContext,
)

PREVIEW_CHARS = 200


def _preview(value: object) -> str:
    text = str(value).replace("\n", "\\n")
    return text if len(text) <= PREVIEW_CHARS else text[:PREVIEW_CHARS] + "…"


async def print_tool_events(ctx: RunContext[Any], events: AsyncIterable[AgentStreamEvent]) -> None:
    async for event in events:
        if isinstance(event, FunctionToolCallEvent):
            line = f"→ {event.part.tool_name}({_preview(event.part.args_as_json_str())})"
        elif isinstance(event, FunctionToolResultEvent):
            if isinstance(event.part, RetryPromptPart):
                line = f"✗ {event.part.tool_name}: {_preview(event.part.content)}"
            else:
                line = f"← {event.part.tool_name}: {_preview(event.part.content)}"
        else:
            continue
        print(line, file=sys.stderr, flush=True)
