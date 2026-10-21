import pytest
from pydantic_ai import UserError
from pydantic_ai.exceptions import (
    ModelConnectionError,
    ModelHTTPError,
    ModelOverloadedError,
    ModelQuotaExceededError,
    ModelRateLimitError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)

from taskly_test_agent.errors import ExitCode, classify


def http_error(category: type[ModelHTTPError] | None, status: int, message: str) -> ModelHTTPError:
    body = {"type": "error", "error": {"type": "x", "message": message}}
    if category is None:
        return ModelHTTPError(status, "some-model", body)
    return ModelHTTPError.for_category(category, status_code=status, model_name="m", body=body)


def test_quota_is_fatal_and_shows_provider_message_only() -> None:
    failure = classify(http_error(ModelQuotaExceededError, 400, "Your credit balance is too low."))

    assert failure is not None
    assert failure.code == ExitCode.PROVIDER_FATAL
    assert str(failure) == "error [quota]: Your credit balance is too low."


def test_auth_error_is_fatal_with_status_kind() -> None:
    failure = classify(http_error(None, 401, "invalid x-api-key"))

    assert failure is not None
    assert (failure.code, failure.kind, failure.message) == (
        ExitCode.PROVIDER_FATAL,
        "http_401",
        "invalid x-api-key",
    )


@pytest.mark.parametrize(
    "exc",
    [
        http_error(ModelRateLimitError, 429, "slow down"),
        http_error(ModelOverloadedError, 529, "overloaded"),
        ModelConnectionError("m", "connection reset"),
    ],
)
def test_transient_errors_are_retryable(exc: Exception) -> None:
    failure = classify(exc)

    assert failure is not None
    assert failure.code == ExitCode.PROVIDER_TRANSIENT


def test_missing_api_key_is_config_error_with_first_sentence_only() -> None:
    failure = classify(
        UserError("Set the `X_API_KEY` environment variable. To try Pydantic AI without a key...")
    )

    assert failure is not None
    assert failure.code == ExitCode.CONFIG
    assert failure.message == "Set the `X_API_KEY` environment variable"


@pytest.mark.parametrize(
    ("exc", "kind"),
    [
        (UnexpectedModelBehavior("Exceeded maximum output retries (1)"), "model_behavior"),
        (UsageLimitExceeded("The next request would exceed the request_limit of 20. See docs"), "usage_limit"),
    ],
)
def test_agent_failures(exc: Exception, kind: str) -> None:
    failure = classify(exc)

    assert failure is not None
    assert (failure.code, failure.kind) == (ExitCode.AGENT_FAILED, kind)


def test_unknown_exceptions_are_left_to_crash() -> None:
    assert classify(ValueError("bug")) is None
