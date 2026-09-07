from __future__ import annotations

import time
from typing import Callable, TypeVar

import anthropic

T = TypeVar("T")

RETRYABLE_ERRORS = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.OverloadedError,
    anthropic.ServiceUnavailableError,
)


class ClaudeUnavailableError(RuntimeError):
    """Raised after retries are exhausted. Callers should hard-fail, never guess."""


def with_retries(fn: Callable[[], T], *, retries: int = 3, base_delay: float = 1.0, label: str = "claude call") -> T:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except RETRYABLE_ERRORS as exc:
            last_exc = exc
            if attempt == retries:
                break
            delay = base_delay * (2**attempt)
            time.sleep(delay)
        except anthropic.APIStatusError:
            # 4xx validation errors are real bugs, not transient - fail immediately.
            raise
    raise ClaudeUnavailableError(
        f"{label} failed after {retries} retries: {last_exc}"
    ) from last_exc
