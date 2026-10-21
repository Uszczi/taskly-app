"""Map run failures to one-line messages and stable exit codes.

Exit codes let the CI workflow decide what to do without parsing text:
retry on PROVIDER_TRANSIENT, fail fast and tell the maintainer on the rest.
"""

from dataclasses import dataclass
from enum import IntEnum

from pydantic_ai import UserError
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelConnectionError,
    ModelContextWindowExceededError,
    ModelHTTPError,
    ModelQuotaExceededError,
    ModelRateLimitError,
    ModelRequestTimeout,
    ModelServerError,
    ModelUnavailableError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)


class ExitCode(IntEnum):
    OK = 0
    CONFIG = 3  # unknown model, missing API key
    PROVIDER_TRANSIENT = 4  # rate limit, overload, 5xx, network: worth retrying
    PROVIDER_FATAL = 5  # billing, auth, bad request, context window: retrying won't help
    AGENT_FAILED = 6  # model misbehaved or ran out of budget
    TESTS_FAILED = 7  # a written test file failed its last run or was never run


@dataclass(frozen=True)
class Failure:
    code: ExitCode
    kind: str
    message: str

    def __str__(self) -> str:
        return f"error [{self.kind}]: {self.message}"


_TRANSIENT = (
    ModelRateLimitError,
    ModelUnavailableError,
    ModelServerError,
    ModelConnectionError,
    ModelRequestTimeout,
)

_FATAL_KINDS: tuple[tuple[type[ModelAPIError], str], ...] = (
    (ModelQuotaExceededError, "quota"),
    (ModelContextWindowExceededError, "context_window"),
)


def provider_message(exc: ModelAPIError) -> str:
    """The provider's own error text, without the SDK's dict dump around it."""
    body = exc.body if isinstance(exc, ModelHTTPError) else None
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(body.get("message"), str):
            return body["message"]
    return str(exc)


def classify(exc: Exception) -> Failure | None:
    """Return a Failure for errors we know how to report, None for real bugs."""
    if isinstance(exc, UserError):
        return Failure(ExitCode.CONFIG, "config", str(exc).split(". ")[0])
    if isinstance(exc, _TRANSIENT):
        return Failure(ExitCode.PROVIDER_TRANSIENT, "provider_transient", provider_message(exc))
    for cls, kind in _FATAL_KINDS:
        if isinstance(exc, cls):
            return Failure(ExitCode.PROVIDER_FATAL, kind, provider_message(exc))
    if isinstance(exc, ModelHTTPError):
        return Failure(
            ExitCode.PROVIDER_FATAL, f"http_{exc.status_code}", provider_message(exc)
        )
    if isinstance(exc, ModelAPIError):
        return Failure(ExitCode.PROVIDER_FATAL, "provider", provider_message(exc))
    if isinstance(exc, UsageLimitExceeded):
        return Failure(ExitCode.AGENT_FAILED, "usage_limit", str(exc).split(". ")[0])
    if isinstance(exc, UnexpectedModelBehavior):
        return Failure(ExitCode.AGENT_FAILED, "model_behavior", str(exc))
    return None
