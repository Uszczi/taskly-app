"""Human-readable token and cost summary for one agent run."""

from pydantic_ai import RunUsage


def format_usage(usage: RunUsage, model: str) -> str:
    if usage.cost is not None:
        cost = f"${usage.cost:.6f}"
    elif usage.requests == 0:
        cost = "$0 (no requests made)"
    else:
        cost = "unknown (no price data for this model)"
    lines = [
        f"── usage: {model} ──",
        f"requests:        {usage.requests}",
        f"tool calls:      {usage.tool_calls}",
        f"input tokens:    {usage.input_tokens:,}"
        f" (cache read {usage.cache_read_tokens:,}, cache write {usage.cache_write_tokens:,})",
        f"output tokens:   {usage.output_tokens:,} (reasoning {usage.output_reasoning_tokens:,})",
        f"total tokens:    {usage.total_tokens:,}",
        f"cost:            {cost}",
    ]
    return "\n".join(lines)
