"""
Error response formatter for ZenX Bridge Skill v1.1.0

Builds standardized JSON error/success responses with:
- Structured error format (code, category, retryable, suggestions)
- Success response wrapper
- Pre-built suggestion and recovery action templates
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from error_codes import ErrorCategory, ErrorCode


# Suggestion templates for common errors
SUGGESTIONS_TIMEOUT = [
    "Check if the browser is responding",
    "Try increasing the timeout value",
    "Verify the target element exists on the page",
]

SUGGESTIONS_CONNECTION_LOST = [
    "Ensure the bsk daemon is running: bsk status",
    "Check if port 52800 is accessible",
    "Restart the daemon with: bsk daemon restart",
]

SUGGESTIONS_INVALID_PARAMS = [
    "Review the command parameters",
    "Check the SKILL.md documentation for correct syntax",
    "Validate input values against expected types",
]

SUGGESTIONS_AUTH_FAILED = [
    "Verify your authentication credentials",
    "Check if the session has expired",
    "Re-authenticate with: bsk auth login",
]

SUGGESTIONS_DAEMON_CRASHED = [
    "Restart the bsk daemon",
    "Check daemon logs for crash details",
    "Report the issue if it persists",
]

SUGGESTION_MAP = {
    "TIMEOUT": SUGGESTIONS_TIMEOUT,
    "CONNECTION_LOST": SUGGESTIONS_CONNECTION_LOST,
    "INVALID_PARAMS": SUGGESTIONS_INVALID_PARAMS,
    "AUTH_FAILED": SUGGESTIONS_AUTH_FAILED,
    "DAEMON_CRASHED": SUGGESTIONS_DAEMON_CRASHED,
}

# Recovery action templates
RECOVERY_CHECK_DAEMON = {
    "action": "check_daemon_status",
    "command": "bsk status",
    "description": "Verify daemon is running and responsive",
}

RECOVERY_RESTART_SESSION = {
    "action": "restart_session",
    "command": "bsk session stop <id> && bsk session start",
    "description": "Stop current session and start a new one",
}

RECOVERY_CHECK_NETWORK = {
    "action": "check_network_connectivity",
    "command": "ping localhost -n 1",
    "description": "Test basic network connectivity to localhost",
}

RECOVERY_MAP = {
    "TIMEOUT": [RECOVERY_RESTART_SESSION],
    "CONNECTION_LOST": [RECOVERY_CHECK_DAEMON, RECOVERY_CHECK_NETWORK],
    "DAEMON_CRASHED": [RECOVERY_CHECK_DAEMON, RECOVERY_RESTART_SESSION],
}


class ErrorResponseBuilder:
    """
    Builds structured error responses with rich context.

    Usage:
        builder = ErrorResponseBuilder()
        response = builder.format_error(
            error_code=TIMEOUT,
            action="tab list",
            session_id="abc123"
        )
        print(json.dumps(response, indent=2))
    """

    def __init__(self):
        self._request_id = str(uuid.uuid4())

    def format_error(
        self,
        error_code: ErrorCode,
        action: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        recovery_actions: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Format an error into a structured JSON response.

        Args:
            error_code: The ErrorCode instance
            action: The action that triggered the error
            session_id: Active session ID if applicable
            details: Additional error context
            suggestions: Custom suggestions (auto-populated if not provided)
            recovery_actions: Custom recovery actions (auto-populated if not provided)

        Returns:
            Dictionary ready for JSON serialization
        """
        # Auto-populate suggestions from template if not provided
        if suggestions is None:
            suggestions = SUGGESTION_MAP.get(error_code.code, ["See documentation for troubleshooting"])

        # Auto-populate recovery actions from template if not provided
        if recovery_actions is None:
            recovery_actions = RECOVERY_MAP.get(error_code.code, [])

        response = {
            "success": False,
            "error": {
                "code": error_code.code,
                "message": error_code.message,
                "category": error_code.category.value,
                "retryable": error_code.retryable,
                "http_status_analogy": error_code.http_status_analogy,
                "suggestions": suggestions,
                "recovery_actions": recovery_actions,
            },
            "context": {
                "action": action,
                "session_id": session_id,
                "details": details or {},
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": self._request_id,
        }

        return response

    def format_success(
        self,
        data: Any,
        action: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Wrap a successful result in a standard response envelope.

        Args:
            data: The result data (dict, list, or primitive)
            action: The completed action
            session_id: Session ID if applicable
            metadata: Additional metadata about the operation

        Returns:
            Dictionary ready for JSON serialization
        """
        response = {
            "success": True,
            "data": data,
            "context": {
                "action": action,
                "session_id": session_id,
                "metadata": metadata or {},
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": self._request_id,
        }

        return response

    def to_json(self, response: Dict[str, Any], pretty: bool = False) -> str:
        """Serialize response dictionary to JSON string."""
        if pretty:
            return json.dumps(response, indent=2, ensure_ascii=False)
        return json.dumps(response, ensure_ascii=False)


# Convenience functions for quick usage
def build_error_response(
    error_code: ErrorCode,
    **kwargs
) -> Dict[str, Any]:
    """Quick helper to build an error response."""
    builder = ErrorResponseBuilder()
    return builder.format_error(error_code, **kwargs)


def build_success_response(
    data: Any,
    **kwargs
) -> Dict[str, Any]:
    """Quick helper to build a success response."""
    builder = ErrorResponseBuilder()
    return builder.format_success(data, **kwargs)
