"""
Input validation and security sanitization layer for ZenX Bridge Skill v1.1.0

Implements Fail-Fast pattern with:
- Parameter type checking and coercion
- Value range and format validation
- Security sanitization (XSS, injection prevention)
- Custom validation rules for bsk commands
"""

import re
import json
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from error_codes import ErrorCode, VALIDATION_FAILED, INVALID_PARAMS


class ValidationSeverity(Enum):
    """Severity levels for validation failures."""

    ERROR = "ERROR"       # Operation-blocking error
    WARNING = "WARNING"   # Non-blocking but noteworthy
    INFO = "INFO"         # Informational only


@dataclass
class ValidationResult:
    """
    Result of a single validation check.

    Attributes:
        is_valid: Whether the value passed validation
        field_name: Name of the validated field
        message: Human-readable description of the issue (if invalid)
        severity: How critical the failure is
        sanitized_value: The cleaned/sanitized version of the input
    """

    is_valid: bool
    field_name: str
    message: str = ""
    severity: ValidationSeverity = ValidationSeverity.ERROR
    sanitized_value: Any = None


@dataclass
class ValidationReport:
    """
    Aggregated report for multiple validations.

    Contains all individual results plus overall status.
    """

    results: List[ValidationResult] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if no ERROR-level failures exist."""
        return not any(
            r.is_valid is False and r.severity == ValidationSeverity.ERROR
            for r in self.results
        )

    @property
    def errors(self) -> List[ValidationResult]:
        """Only ERROR-level failures."""
        return [r for r in self.results if r.is_valid is False and r.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationResult]:
        """Only WARNING-level issues."""
        return [r for r in self.results if r.is_valid is False and r.severity == ValidationSeverity.WARNING]

    def add_result(self, result: ValidationResult):
        """Append a validation result."""
        self.results.append(result)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "results": [
                {
                    "field": r.field_name,
                    "valid": r.is_valid,
                    "message": r.message,
                    "severity": r.severity.value,
                    "sanitized_value": r.sanitized_value,
                }
                for r in self.results
            ],
        }


class InputValidator:
    """
    Centralized input validation and security sanitization.

    Usage:
        validator = InputValidator()
        report = validator.validate({
            "session_id": "abc123",
            "timeout": 30,
            "url": "https://example.com",
        }, rules="bsk_command")

        if not report.is_valid:
            raise ValidationError(report)
    """

    # Security patterns
    DANGEROUS_PATTERNS = [
        (r'<script\b[^>]*>.*?</script>', 'Script tag detected'),
        (r'javascript\s*:', 'JavaScript protocol detected'),
        (r'on\w+\s*=', 'Event handler attribute detected'),
        (r'[\x00-\x1f\x7f]', 'Control character detected'),
        (r';\s*(drop|delete|truncate|insert|update)\b', 'SQL-like injection pattern',),
        (r'\$\{.*?\}', 'Template expression detected'),
        (r'`[^`]*`', 'Backtick command substitution detected'),
    ]

    # BSK-specific validation rules
    SESSION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{8,64}$')
    URL_PATTERN = re.compile(r'^https?://[^\s<>"]{1,2048}$')
    SELECTOR_PATTERN = re.compile(r'^[a-zA-Z][\w\-\.#:\[\]>*+~()=^$|,"\' ]{0,500}$')
    TIMEOUT_RANGE = (1, 600)

    def __init__(self, strict_mode: bool = True):
        """
        Initialize validator.

        Args:
            strict_mode: If True, fail on first ERROR; if False, collect all errors.
        """
        self.strict_mode = strict_mode
        self._report = ValidationReport()

    def validate(
        self,
        data: Dict[str, Any],
        ruleset: str = "default"
    ) -> ValidationReport:
        """
        Validate a dictionary of inputs against a ruleset.

        Args:
            data: Dictionary of field names to values
            ruleset: Which validation rules to apply ("default", "bsk_command", "url", etc.)

        Returns:
            ValidationReport with all results
        """
        self._report = ValidationReport()

        for field_name, value in data.items():
            self._validate_field(field_name, value, ruleset)

        return self._report

    def _validate_field(
        self,
        field_name: str,
        value: Any,
        ruleset: str
    ):
        """Apply appropriate validators based on field name and ruleset."""
        # Type check - reject None unless explicitly allowed
        if value is None:
            self._report.add_result(ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"Field '{field_name}' cannot be null/None",
                severity=ValidationSeverity.ERROR,
                sanitized_value=None,
            ))
            return

        # Field-specific validators
        validators_map = {
            "session_id": self._validate_session_id,
            "url": self._validate_url,
            "selector": self._validate_selector,
            "timeout": self._validate_timeout,
            "command": self._validate_command,
            "action": self._validate_action,
            "text": self._validate_text_input,
            "value": self._validate_text_input,
            "filename": self._validate_filename,
        }

        validator_func = validators_map.get(field_name)
        if validator_func:
            result = validator_func(value)
            result.field_name = field_name
            self._report.add_result(result)
        else:
            # Default: apply security sanitization only
            result = self._sanitize_value(value)
            result.field_name = field_name
            self._report.add_result(result)

    def _validate_session_id(self, value: str) -> ValidationResult:
        """Validate session ID format."""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message="Session ID must be a string",
                sanitized_value=str(value) if value else "",
            )

        if not self.SESSION_ID_PATTERN.match(value):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message=(
                    f"Invalid session ID format. "
                    f"Expected 8-64 alphanumeric characters, underscores, or hyphens. "
                    f"Got: '{value[:20]}...'"
                ),
                sanitized_value=self.SESSION_ID_PATTERN.sub("", value),
            )

        return ValidationResult(is_valid=True, field_name="", sanitized_value=value)

    def _validate_url(self, value: str) -> ValidationResult:
        """Validate URL safety and format."""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message="URL must be a string",
                sanitized_value="",
            )

        # Length check
        if len(value) > 2048:
            return ValidationResult(
                is_valid=False,
                field_name="",
                message=f"URL too long ({len(value)} chars, max 2048)",
                sanitized_value=value[:2048],
            )

        # Format check
        if not self.URL_PATTERN.match(value):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message=(
                    f"Invalid URL format. Must start with http:// or https:// "
                    f"and contain no whitespace or dangerous characters."
                ),
                severity=ValidationSeverity.ERROR,
                sanitized_value=re.sub(r'[^\w\-._~:/?#\[\]!$&\'()*+,;%=]', '', value),
            )

        # Security check
        security_result = self._check_security_patterns(value)
        if not security_result.is_valid:
            return security_result

        return ValidationResult(is_valid=True, field_name="", sanitized_value=value)

    def _validate_selector(self, value: str) -> ValidationResult:
        """Validate CSS/XPath selector safety."""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message="Selector must be a string",
                sanitized_value="",
            )

        if len(value) > 500:
            return ValidationResult(
                is_valid=False,
                field_name="",
                message=f"Selector too long ({len(value)} chars, max 500)",
                sanitized_value=value[:500],
            )

        if not self.SELECTOR_PATTERN.match(value):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message="Invalid selector format. Contains disallowed characters.",
                severity=ValidationSeverity.ERROR,
                sanitized_value=re.sub(r'[^\w\-.#:\[\]>*+~()=^$|,"\' ]', '', value),
            )

        return ValidationResult(is_valid=True, field_name="", sanitized_value=value)

    def _validate_timeout(self, value: Union[int, float]) -> ValidationResult:
        """Validate timeout is within acceptable range."""
        try:
            numeric_value = int(value)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message=f"Timeout must be numeric, got {type(value).__name__}",
                sanitized_value=30,  # Safe default
            )

        min_val, max_val = self.TIMEOUT_RANGE
        if not (min_val <= numeric_value <= max_val):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message=(
                    f"Timeout out of range. Must be between {min_val}s and {max_val}s, "
                    f"got {numeric_value}"
                ),
                severity=ValidationSeverity.WARNING,  # Allow but warn
                sanitized_value=max(min_val, min(numeric_value, max_val)),
            )

        return ValidationResult(is_valid=True, field_name="", sanitized_value=numeric_value)

    def _validate_command(self, value: str) -> ValidationResult:
        """Validate bsk command name."""
        valid_commands = {
            "session", "tab", "navigate", "click", "type", "scroll",
            "screenshot", "snapshot", "wait", "invoke", "status",
            "daemon", "element", "form", "network",
        }

        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message="Command must be a string",
                sanitized_value="",
            )

        if value.lower().strip() not in valid_commands:
            return ValidationResult(
                is_valid=False,
                field_name="",
                message=(
                    f"Unknown command: '{value}'. "
                    f"Valid commands: {', '.join(sorted(valid_commands))}"
                ),
                severity=ValidationSeverity.ERROR,
                sanitized_value=value.lower().strip(),
            )

        return ValidationResult(is_valid=True, field_name="", sanitized_value=value.lower().strip())

    def _validate_action(self, value: str) -> ValidationResult:
        """Validate action name (sub-command)."""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message="Action must be a string",
                sanitized_value="",
            )

        if len(value) < 1 or len(value) > 100:
            return ValidationResult(
                is_valid=False,
                field_name="",
                message="Action must be 1-100 characters",
                sanitized_value=value[:100],
            )

        # Basic alphanumeric + hyphen/underscore check
        if not re.match(r'^[a-z][a-z0-9_\-]*$', value.lower()):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message=(
                    f"Invalid action format. Must start with letter, "
                    f"contain only lowercase letters, numbers, hyphens, underscores."
                ),
                severity=ValidationSeverity.ERROR,
                sanitized_value=re.sub(r'[^a-z0-9_\-]', '', value.lower()),
            )

        return ValidationResult(is_valid=True, field_name="", sanitized_value=value.lower())

    def _validate_text_input(self, value: str) -> ValidationResult:
        """General text input with security sanitization."""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=True,
                field_name="",
                message="Converted non-string input to string",
                severity=ValidationSeverity.INFO,
                sanitized_value=str(value),
            )

        if len(value) > 100000:  # 100KB limit for text inputs
            return ValidationResult(
                is_valid=False,
                field_name="",
                message=f"Text input too large ({len(value)} bytes, max 100KB)",
                severity=ValidationSeverity.ERROR,
                sanitized_value=value[:100000],
            )

        # Apply security checks
        security_result = self._check_security_patterns(value)
        if not security_result.is_valid:
            return security_result

        return ValidationResult(is_valid=True, field_name="", sanitized_value=value)

    def _validate_filename(self, value: str) -> ValidationResult:
        """Validate filename for path traversal prevention."""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                field_name="",
                message="Filename must be a string",
                sanitized_value="output.txt",
            )

        # Path traversal detection
        dangerous_patterns = ['..', '/', '\\', '\x00']
        for pattern in dangerous_patterns:
            if pattern in value:
                return ValidationResult(
                    is_valid=False,
                    field_name="",
                    message=f"Dangerous filename pattern detected: '{pattern}'",
                    severity=ValidationSeverity.ERROR,
                    sanitized_value=re.sub(r'[/\\\x00]|\\.\\.', '_', value),
                )

        # Extension whitelist (common safe extensions)
        safe_extensions = {'.txt', '.json', '.csv', '.png', '.jpg', '.html', '.pdf'}
        import os
        _, ext = os.path.splitext(value)
        if ext.lower() not in safe_extensions and ext != '':
            return ValidationResult(
                is_valid=False,
                field_name="",
                message=f"Potentially unsafe file extension: '{ext}'",
                severity=ValidationSeverity.WARNING,
                sanitized_value=os.path.splitext(value)[0] + ".txt",
            )

        return ValidationResult(is_valid=True, field_name="", sanitized_value=value)

    def _check_security_patterns(self, value: str) -> ValidationResult:
        """Check for dangerous patterns (XSS, injection, etc.)."""
        if not isinstance(value, str):
            return ValidationResult(is_valid=True, field_name="", sanitized_value=value)

        for pattern_tuple in self.DANGEROUS_PATTERNS:
            pattern = pattern_tuple[0]
            description = pattern_tuple[1]
            match = re.search(pattern, value, re.IGNORECASE | re.DOTALL)
            if match:
                sanitized = re.sub(pattern, '[REDACTED]', value, flags=re.IGNORECASE | re.DOTALL)
                return ValidationResult(
                    is_valid=False,
                    field_name="",
                    message=f"Security violation: {description} at position {match.start()}",
                    severity=ValidationSeverity.ERROR,
                    sanitized_value=sanitized,
                )

        return ValidationResult(is_valid=True, field_name="", sanitized_value=value)

    def _sanitize_value(self, value: Any) -> ValidationResult:
        """Apply basic sanitization for unknown fields."""
        if isinstance(value, str):
            return self._check_security_patterns(value)
        elif isinstance(value, (int, float, bool)):
            return ValidationResult(is_valid=True, field_name="", sanitized_value=value)
        elif isinstance(value, (list, dict)):
            # Recursively sanitize collections
            try:
                sanitized_json = json.dumps(value, ensure_ascii=False)
                return self._check_security_patterns(sanitized_json)
            except (TypeError, ValueError):
                return ValidationResult(
                    is_valid=False,
                    field_name="",
                    message="Cannot serialize complex object for validation",
                    severity=ValidationSeverity.WARNING,
                    sanitized_value=str(value),
                )
        else:
            return ValidationResult(
                is_valid=True,
                field_name="",
                message=f"Unhandled type {type(value).__name__}",
                severity=ValidationSeverity.INFO,
                sanitized_value=value,
            )


# Convenience function for quick validation
def validate_bsk_params(**kwargs) -> Tuple[bool, ValidationReport]:
    """
    Quick validation helper for bsk command parameters.

    Usage:
        is_valid, report = validate_bsk_params(
            session_id="abc123",
            timeout=30,
            url="https://example.com",
        )
        if not is_valid:
            print(report.errors)

    Returns:
        Tuple of (is_valid, ValidationReport)
    """
    validator = InputValidator()
    report = validator.validate(kwargs, ruleset="bsk_command")
    return (report.is_valid, report)


def sanitize_string(value: str) -> str:
    """
    Quick sanitization for a single string value.

    Removes dangerous patterns while preserving safe content.
    """
    validator = InputValidator(strict_mode=False)
    result = validator._check_security_patterns(value)
    return result.sanitized_value if result.sanitized_value else value
