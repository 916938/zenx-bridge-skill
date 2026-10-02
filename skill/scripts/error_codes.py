"""
Error codes and classification system for ZenX Bridge Skill v1.1.0

Defines the foundational error taxonomy used across all error handling modules:
- Error categories (TRANSIENT, PERMANENT, SYSTEM, USER_ERROR)
- Error code dataclass with retryability metadata
- Exit code mapping table
- Exception classification utility
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ErrorCategory(Enum):
    """Error classification for retry and recovery decisions."""

    TRANSIENT = "TRANSIENT"       # Auto-retry safe (network timeouts, temporary failures)
    PERMANENT = "PERMANENT"       # Manual fix required (invalid params, auth failures)
    SYSTEM = "SYSTEM"             # Admin intervention needed (daemon crash, port conflicts)
    USER_ERROR = "USER_ERROR"     # User action required (session expired, confirmation needed)


@dataclass(frozen=True)
class ErrorCode:
    """
    Machine-readable error identifier with rich context.

    Attributes:
        code: Short identifier like "TIMEOUT", "CONNECTION_LOST"
        message: Human-readable description
        category: Error classification for retry logic
        retryable: Whether automatic retry is recommended
        http_status_analogy: HTTP status code for API compatibility
    """

    code: str
    message: str
    category: ErrorCategory
    retryable: bool
    http_status_analogy: int


# Predefined error constants
TIMEOUT = ErrorCode(
    code="TIMEOUT",
    message="Operation timed out",
    category=ErrorCategory.TRANSIENT,
    retryable=True,
    http_status_analogy=504,
)

CONNECTION_LOST = ErrorCode(
    code="CONNECTION_LOST",
    message="Connection to daemon lost",
    category=ErrorCategory.TRANSIENT,
    retryable=True,
    http_status_analogy=503,
)

INVALID_PARAMS = ErrorCode(
    code="INVALID_PARAMS",
    message="Invalid parameters provided",
    category=ErrorCategory.PERMANENT,
    retryable=False,
    http_status_analogy=400,
)

AUTH_FAILED = ErrorCode(
    code="AUTH_FAILED",
    message="Authentication failed",
    category=ErrorCategory.PERMANENT,
    retryable=False,
    http_status_analogy=401,
)

DAEMON_CRASHED = ErrorCode(
    code="DAEMON_CRASHED",
    message="BrowserSkill daemon crashed",
    category=ErrorCategory.SYSTEM,
    retryable=False,
    http_status_analogy=503,
)

SESSION_EXPIRED = ErrorCode(
    code="SESSION_EXPIRED",
    message="Browser session has expired or been closed",
    category=ErrorCategory.USER_ERROR,
    retryable=False,
    http_status_analogy=410,
)

NOT_FOUND = ErrorCode(
    code="NOT_FOUND",
    message="Requested resource not found (tab, element, etc.)",
    category=ErrorCategory.PERMANENT,
    retryable=False,
    http_status_analogy=404,
)

RATE_LIMITED = ErrorCode(
    code="RATE_LIMITED",
    message="Too many requests, rate limit exceeded",
    category=ErrorCategory.TRANSIENT,
    retryable=True,
    http_status_analogy=429,
)

INTERNAL_ERROR = ErrorCode(
    code="INTERNAL_ERROR",
    message="Internal daemon error",
    category=ErrorCategory.SYSTEM,
    retryable=False,
    http_status_analogy=500,
)

BROWSER_NOT_READY = ErrorCode(
    code="BROWSER_NOT_READY",
    message="Browser is not ready for interaction",
    category=ErrorCategory.TRANSIENT,
    retryable=True,
    http_status_analogy=503,
)

VALIDATION_FAILED = ErrorCode(
    code="VALIDATION_FAILED",
    message="Input validation failed - see details",
    category=ErrorCategory.PERMANENT,
    retryable=False,
    http_status_analogy=422,
)

CANCELLED = ErrorCode(
    code="CANCELLED",
    message="Operation was cancelled by user or signal",
    category=ErrorCategory.USER_ERROR,
    retryable=False,
    http_status_analogy=499,
)

CONFIGURATION_ERROR = ErrorCode(
    code="CONFIGURATION_ERROR",
    message="Invalid configuration detected",
    category=ErrorCategory.PERMANENT,
    retryable=False,
    http_status_analogy=500,
)

UNKNOWN_ERROR = ErrorCode(
    code="UNKNOWN_ERROR",
    message="An unknown error occurred",
    category=ErrorCategory.SYSTEM,
    retryable=False,
    http_status_analogy=500,
)


# Map bsk CLI exit codes to ErrorCode instances
EXIT_CODE_MAP: dict[int, Optional[ErrorCode]] = {
    0: None,  # Success
    1: INVALID_PARAMS,
    2: TIMEOUT,
    3: CONNECTION_LOST,
    4: AUTH_FAILED,
    5: NOT_FOUND,
}


def get_error_by_code(code: str) -> Optional[ErrorCode]:
    """Lookup ErrorCode by its string identifier."""
    for error in [
        TIMEOUT, CONNECTION_LOST, INVALID_PARAMS, AUTH_FAILED,
        DAEMON_CRASHED, SESSION_EXPIRED, NOT_FOUND, RATE_LIMITED,
        INTERNAL_ERROR, BROWSER_NOT_READY, VALIDATION_FAILED, CANCELLED,
        CONFIGURATION_ERROR, UNKNOWN_ERROR,
    ]:
        if error.code == code:
            return error
    return None


def get_error_by_exit_code(exit_code: int) -> Optional[ErrorCode]:
    """Map a bsk CLI exit code to an ErrorCode."""
    return EXIT_CODE_MAP.get(exit_code)


def classify_exception(exception: Exception) -> ErrorCode:
    """
    Classify a Python exception into our error taxonomy.

    Args:
        exception: The exception to classify

    Returns:
        Appropriate ErrorCode instance
    """
    if isinstance(exception, TimeoutError):
        return TIMEOUT
    elif isinstance(exception, ConnectionError):
        return CONNECTION_LOST
    elif isinstance(exception, (ValueError, TypeError)):
        return INVALID_PARAMS
    elif isinstance(exception, PermissionError):
        return AUTH_FAILED
    elif isinstance(exception, (FileNotFoundError, KeyError)):
        return NOT_FOUND
    elif isinstance(exception, RuntimeError):
        # Check for common patterns in RuntimeError messages
        msg = str(exception).lower()
        if "timeout" in msg:
            return TIMEOUT
        elif "connection" in msg or "refused" in msg:
            return CONNECTION_LOST
        elif "daemon" in msg or "crash" in msg:
            return DAEMON_CRASHED
        else:
            return INTERNAL_ERROR
    else:
        return UNKNOWN_ERROR
