"""
Smart retry handler with exponential backoff and jitter for ZenX Bridge Skill v1.1.0

Implements resilient retry logic:
- Exponential backoff (1s → 2s → 4s → 8s)
- Jitter (±20%) to prevent thundering herd
- Retry only on transient errors (TIMEOUT, CONNECTION_LOST)
- Configurable max retries and timeout
"""

import time
import random
import functools
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field

from error_codes import (
    ErrorCategory,
    ErrorCode,
    TIMEOUT,
    CONNECTION_LOST,
    RATE_LIMITED,
    BROWSER_NOT_READY,
    get_error_by_exit_code,
)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds before first retry (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 30.0)
        backoff_multiplier: Exponential growth factor (default: 2.0)
        jitter_percentage: Random jitter as decimal (default: 0.2 for ±20%)
        retryable_errors: Set of error codes that trigger retries
        retry_on_exceptions: Exception types to catch and retry
        overall_timeout: Total time limit for all attempts combined (default: 60s)
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_multiplier: float = 2.0
    jitter_percentage: float = 0.2
    retryable_errors: set = field(default_factory=lambda: {
        TIMEOUT,
        CONNECTION_LOST,
        RATE_LIMITED,
        BROWSER_NOT_READY,
    })
    retry_on_exceptions: tuple = (ConnectionError, TimeoutError)
    overall_timeout: float = 60.0


@dataclass
class AttemptResult:
    """
    Result of a single retry attempt.

    Attributes:
        attempt_number: Which attempt this is (1-indexed)
        success: Whether the attempt succeeded
        result: Return value if successful
        error: Error code if failed
        exception: Exception if raised
        delay_before: How long we waited before this attempt
        duration: How long the attempt took
    """

    attempt_number: int
    success: bool
    result: Optional[T] = None
    error: Optional[ErrorCode] = None
    exception: Optional[Exception] = None
    delay_before: float = 0.0
    duration: float = 0.0


@dataclass
class RetrySummary:
    """
    Summary of all retry attempts.

    Provides statistics and final outcome.
    """

    total_attempts: int
    succeeded: bool
    final_result: Optional[T] = None
    final_error: Optional[ErrorCode] = None
    attempts: List[AttemptResult] = field(default_factory=list)

    @property
    def total_time_spent(self) -> float:
        """Total time including delays and execution."""
        return sum(a.delay_before + a.duration for a in self.attempts)

    @property
    def was_retried(self) -> bool:
        """Whether any retries occurred."""
        return self.total_attempts > 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/monitoring."""
        return {
            "succeeded": self.succeeded,
            "total_attempts": self.total_attempts,
            "was_retried": self.was_retried,
            "total_time_spent_s": round(self.total_time_spent, 2),
            "final_error": self.final_error.code if self.final_error else None,
        }


class RetryHandler:
    """
    Manages retry logic with exponential backoff.

    Usage:
        handler = RetryHandler(RetryConfig(max_retries=3))

        @handler.retry
        def fetch_data():
            return bsk("tab list")

        result, summary = fetch_data()
        if not summary.succeeded:
            print(f"Failed after {summary.total_attempts} attempts")
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (0-indexed, delay for retry after this attempt)

        Returns:
            Delay in seconds (with jitter applied). Returns 0 for first attempt (no pre-delay).
        """
        # No delay before the initial attempt
        if attempt < 1:
            return 0.0

        # Exponential backoff: base * multiplier^(attempt-1) for retry #attempt
        effective_attempt = attempt - 1
        exponential_delay = self.config.base_delay * (self.config.backoff_multiplier ** effective_attempt)

        # Cap at maximum delay
        capped_delay = min(exponential_delay, self.config.max_delay)

        # Apply random jitter (±jitter_percentage)
        jitter_range = capped_delay * self.config.jitter_percentage
        actual_delay = capped_delay + random.uniform(-jitter_range, jitter_range)

        # Ensure non-negative
        return max(0.0, actual_delay)

    def should_retry(
        self,
        error: Optional[ErrorCode] = None,
        exception: Optional[Exception] = None,
        exit_code: Optional[int] = None,
        current_attempt: int = 0,
    ) -> bool:
        """
        Determine if a failure warrants a retry.

        Args:
            error: ErrorCode from classification
            exception: Python exception that occurred
            exit_code: Process exit code if applicable
            current_attempt: Which attempt just failed (0-indexed)

        Returns:
            True if we should retry
        """
        # Check max retries
        if current_attempt >= self.config.max_retries:
            return False

        # Check by ErrorCode
        if error is not None:
            return error in self.config.retryable_errors

        # Check by exception type
        if exception is not None:
            return isinstance(exception, self.config.retry_on_exceptions)

        # Check by exit code (map to ErrorCode then check)
        if exit_code is not None:
            mapped_error = get_error_by_exit_code(exit_code)
            if mapped_error is not None:
                return mapped_error in self.config.retryable_errors

        # Default: don't retry unknown errors
        return False

    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> Tuple[T, RetrySummary]:
        """
        Execute a function with automatic retry logic.

        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass through

        Returns:
            Tuple of (result, RetrySummary)
        """
        start_time = time.time()
        attempts: List[AttemptResult] = []
        last_error: Optional[ErrorCode] = None
        last_exception: Optional[Exception] = None

        for attempt_num in range(self.config.max_retries + 1):  # +1 for initial attempt
            # Calculate delay before this attempt (except first)
            if attempt_num > 0:
                delay = self.calculate_delay(attempt_num - 1)
                time.sleep(delay)
            else:
                delay = 0.0

            # Execute the function
            attempt_start = time.time()
            try:
                result = func(*args, **kwargs)
                attempt_duration = time.time() - attempt_start

                # Success!
                attempt_result = AttemptResult(
                    attempt_number=attempt_num + 1,
                    success=True,
                    result=result,
                    delay_before=delay,
                    duration=attempt_duration,
                )
                attempts.append(attempt_result)

                summary = RetrySummary(
                    total_attempts=len(attempts),
                    succeeded=True,
                    final_result=result,
                    attempts=attempts,
                )
                return (result, summary)

            except Exception as e:
                attempt_duration = time.time() - attempt_start

                # Classify the exception
                from error_codes import classify_exception
                error_code = classify_exception(e)

                attempt_result = AttemptResult(
                    attempt_number=attempt_num + 1,
                    success=False,
                    error=error_code,
                    exception=e,
                    delay_before=delay,
                    duration=attempt_duration,
                )
                attempts.append(attempt_result)

                last_error = error_code
                last_exception = e

                # Check if we should retry
                if not self.should_retry(error=error_code, exception=e, current_attempt=attempt_num):
                    break

                # Check overall timeout
                elapsed = time.time() - start_time
                if elapsed >= self.config.overall_timeout:
                    break

        # All retries exhausted or non-retryable error
        summary = RetrySummary(
            total_attempts=len(attempts),
            succeeded=False,
            final_error=last_error,
            attempts=attempts,
        )

        # Re-raise the last exception
        if last_exception is not None:
            raise last_exception

        return (None, summary)  # Shouldn't reach here normally

    def retry(self, func: Callable[..., T]) -> Callable[..., Tuple[T, RetrySummary]]:
        """
        Decorator version of execute_with_retry.

        Usage:
            @handler.retry
            def my_function():
                ...

            result, summary = my_function()

        Returns:
            Wrapped function that returns (result, RetrySummary)
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Tuple[T, RetrySummary]:
            return self.execute_with_retry(func, *args, **kwargs)

        return wrapper


# Pre-configured handlers for common use cases
DEFAULT_HANDLER = RetryHandler(RetryConfig())
AGGRESSIVE_HANDLER = RetryHandler(RetryConfig(
    max_retries=5,
    base_delay=0.5,
    max_delay=10.0,
))
CONSERVATIVE_HANDLER = RetryHandler(RetryConfig(
    max_retries=2,
    base_delay=2.0,
    max_delay=15.0,
))


def retry_on_transient_error(
    max_retries: int = 3,
    base_delay: float = 1.0,
    **config_kwargs,
) -> Callable:
    """
    Convenience decorator for quick retry configuration.

    Usage:
        @retry_on_transient_error(max_retries=5)
        def unstable_operation():
            ...

        result, summary = unstable_operation()
    """

    config = RetryConfig(max_retries=max_retries, base_delay=base_delay, **config_kwargs)
    handler = RetryHandler(config)

    def decorator(func: Callable[..., T]) -> Callable[..., Tuple[T, RetrySummary]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Tuple[T, RetrySummary]:
            return handler.execute_with_retry(func, *args, **kwargs)
        return wrapper

    return decorator
