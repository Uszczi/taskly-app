from decimal import Decimal

from pydantic_ai import RunUsage

from taskly_test_agent.usage import format_usage


def test_format_usage_shows_tokens_and_cost() -> None:
    usage = RunUsage(
        requests=3,
        tool_calls=2,
        input_tokens=12_345,
        cache_read_tokens=1_000,
        output_tokens=678,
        output_reasoning_tokens=100,
    )
    usage.cost = Decimal("0.001573")

    text = format_usage(usage, "anthropic:claude-haiku-5-5")

    assert "requests:        3" in text
    assert "input tokens:    12,345 (cache read 1,000, cache write 0)" in text
    assert "output tokens:   678 (reasoning 100)" in text
    assert "total tokens:    13,023" in text
    assert "cost:            $0.001573" in text


def test_format_usage_without_price_data() -> None:
    assert "unknown" in format_usage(RunUsage(requests=1), "ollama:qwen2:7b")


def test_format_usage_without_requests_costs_nothing() -> None:
    assert "cost:            $0 (no requests made)" in format_usage(RunUsage(), "x:y")
