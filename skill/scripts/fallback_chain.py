"""
Graceful degradation fallback chain for ZenX Bridge Skill v1.1.0

Multi-level execution with automatic degradation and decision logging:

- Level 1  passthrough  — raw JSON via `bsk invoke` (bsk 0.2.0+)
- Level 2  legacy       — typed `bsk <command>` subcommands, flattened args
- Level 3  simplified   — strip optional args and retry the legacy path
- Beyond   — structured error with suggestions (error_codes taxonomy)

Which failures escalate: TRANSIENT and SYSTEM errors fall through to the
next level. INVALID_PARAMS / VALIDATION_FAILED also fall through (flattened
or optional arguments are a plausible cause). Other PERMANENT and USER_ERROR
failures stop immediately — switching modes cannot fix a bad session id or
a permission denial.

When every level is exhausted and the final error is SYSTEM-class, the
optional emergency cleanup callback runs (e.g. stop the session) before the
result is returned.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from error_codes import (
    ErrorCategory,
    ErrorCode,
    classify_exception,
    INVALID_PARAMS,
    VALIDATION_FAILED,
)

# Executor contract: (action, args, session) -> Any; raises on failure.
LevelExecutor = Callable[[str, Dict[str, Any], Optional[str]], Any]


class FallbackLevel(Enum):
    """Named levels of the default degradation chain."""

    PASSTHROUGH = "passthrough"
    LEGACY = "legacy"
    SIMPLIFIED = "simplified"


@dataclass(frozen=True)
class LevelSpec:
    """
    One executable level of the chain.

    Attributes:
        level: Level identity (mode name used in decision logs)
        executor: Callable that performs the action; raises on failure
        is_available: Cheap check ran before attempting (e.g. CLI support)
        description: Human-readable purpose of the level
    """

    level: FallbackLevel
    executor: LevelExecutor
    is_available: Callable[[], bool] = lambda: True
    description: str = ""


@dataclass
class AttemptRecord:
    """Decision-log entry for one level attempt."""

    mode: str
    status: str  # success | failed | skipped
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: str = ""
    next_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "status": self.status,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
            "next_action": self.next_action,
        }


@dataclass
class FallbackResult:
    """Final outcome plus the full decision log."""

    succeeded: bool
    value: Any = None
    attempts: List[AttemptRecord] = field(default_factory=list)
    final_error: Optional[ErrorCode] = None

    @property
    def used_fallback(self) -> bool:
        """True when any level failed before the outcome was decided."""
        return any(record.status == "failed" for record in self.attempts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "succeeded": self.succeeded,
            "used_fallback": self.used_fallback,
            "final_error": self.final_error.code if self.final_error else None,
            "attempts": [record.to_dict() for record in self.attempts],
        }


@dataclass
class FallbackConfig:
    """
    Behaviour switches mirroring the documented CLI options:

    - ``--fallback enabled|disabled``
    - ``--fallback-log verbose|quiet``
    - ``--max-fallback-depth <n>`` (default 3)
    """

    enabled: bool = True
    max_depth: int = 3
    log_verbosity: str = "quiet"  # verbose | quiet

    def __post_init__(self) -> None:
        if self.max_depth < 0:
            raise ValueError("max_depth must be non-negative")


def should_fallback(error: ErrorCode) -> bool:
    """Decide whether a failure justifies trying the next level."""
    if error.category in (ErrorCategory.TRANSIENT, ErrorCategory.SYSTEM):
        return True
    return error in (INVALID_PARAMS, VALIDATION_FAILED)


def strip_optional_args(
    args: Dict[str, Any], required_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Reduce an argument dict to the keys required for the action.

    Used by the simplified level: fewer optional knobs, higher chance the
    typed CLI accepts the flattened result.
    """
    required = set(required_keys or [])
    return {key: value for key, value in args.items() if key in required}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class FallbackChain:
    """
    Execute an action through ordered levels, degrading on failure.

    The level list is the extensibility point: construct FallbackChain with
    any sequence of LevelSpec objects (see default_chain for the standard
    three-level setup).
    """

    def __init__(
        self,
        levels: List[LevelSpec],
        config: Optional[FallbackConfig] = None,
        emergency_cleanup: Optional[Callable[[FallbackResult], None]] = None,
    ):
        if not levels:
            raise ValueError("fallback chain requires at least one level")
        self._levels = list(levels)
        self._config = config or FallbackConfig()
        self._emergency_cleanup = emergency_cleanup

    @property
    def config(self) -> FallbackConfig:
        return self._config

    def execute(
        self,
        action: str,
        args: Optional[Dict[str, Any]] = None,
        session: Optional[str] = None,
    ) -> FallbackResult:
        """
        Run the action through the chain.

        Args:
            action: Action name (e.g. "fill", "tab_list")
            args: Argument dict forwarded to each executor
            session: Optional session id forwarded to each executor

        Returns:
            FallbackResult with the value on success, or the classified
            final error plus the complete decision log on failure.
        """
        args = dict(args or {})
        attempts: List[AttemptRecord] = []
        executed = 0
        last_error: Optional[ErrorCode] = None

        for index, spec in enumerate(self._levels):
            next_level = self._levels[index + 1].level.value if index + 1 < len(self._levels) else None

            if not spec.is_available():
                attempts.append(
                    AttemptRecord(
                        mode=spec.level.value,
                        status="skipped",
                        error="level unavailable",
                        timestamp=_now_iso(),
                        next_action=(
                            f"fallback_to_{next_level}" if next_level else "give_up"
                        ),
                    )
                )
                continue

            if self._config.max_depth == 0 or executed >= self._config.max_depth:
                attempts.append(
                    AttemptRecord(
                        mode=spec.level.value,
                        status="skipped",
                        error="max fallback depth reached",
                        timestamp=_now_iso(),
                        next_action="give_up",
                    )
                )
                break

            executed += 1
            start = time.perf_counter()
            try:
                value = spec.executor(action, args, session)
                duration_ms = (time.perf_counter() - start) * 1000
                attempts.append(
                    AttemptRecord(
                        mode=spec.level.value,
                        status="success",
                        duration_ms=duration_ms,
                        timestamp=_now_iso(),
                    )
                )
                return FallbackResult(succeeded=True, value=value, attempts=attempts)
            except Exception as error:  # noqa: BLE001 - classified below
                duration_ms = (time.perf_counter() - start) * 1000
                last_error = classify_exception(error)
                may_fallback = self._config.enabled and should_fallback(last_error)
                if may_fallback and next_level:
                    next_action = f"fallback_to_{next_level}"
                elif may_fallback:
                    next_action = "give_up"
                else:
                    next_action = "stop"
                attempts.append(
                    AttemptRecord(
                        mode=spec.level.value,
                        status="failed",
                        error=f"{last_error.code}: {error}",
                        duration_ms=duration_ms,
                        timestamp=_now_iso(),
                        next_action=next_action,
                    )
                )
                if not may_fallback:
                    result = FallbackResult(
                        succeeded=False, attempts=attempts, final_error=last_error
                    )
                    self._maybe_emergency_cleanup(result)
                    return result

        result = FallbackResult(
            succeeded=False, attempts=attempts, final_error=last_error
        )
        self._maybe_emergency_cleanup(result)
        return result

    def _maybe_emergency_cleanup(self, result: FallbackResult) -> None:
        if (
            self._emergency_cleanup is not None
            and result.final_error is not None
            and result.final_error.category == ErrorCategory.SYSTEM
        ):
            self._emergency_cleanup(result)


def default_chain(
    passthrough_executor: LevelExecutor,
    legacy_executor: LevelExecutor,
    passthrough_available: Callable[[], bool] = lambda: True,
    config: Optional[FallbackConfig] = None,
    emergency_cleanup: Optional[Callable[[FallbackResult], None]] = None,
    required_keys: Optional[List[str]] = None,
) -> FallbackChain:
    """
    Build the standard three-level chain.

    The simplified level reuses the legacy executor with the argument dict
    reduced to ``required_keys`` (pass the action's required parameter names).
    """
    def simplified_executor(action: str, args: Dict[str, Any], session: Optional[str]) -> Any:
        return legacy_executor(action, strip_optional_args(args, required_keys), session)

    levels = [
        LevelSpec(
            level=FallbackLevel.PASSTHROUGH,
            executor=passthrough_executor,
            is_available=passthrough_available,
            description="bsk invoke passthrough (raw JSON)",
        ),
        LevelSpec(
            level=FallbackLevel.LEGACY,
            executor=legacy_executor,
            description="typed bsk subcommand (flattened args)",
        ),
        LevelSpec(
            level=FallbackLevel.SIMPLIFIED,
            executor=simplified_executor,
            description="legacy retry with optional args stripped",
        ),
    ]
    return FallbackChain(levels, config=config, emergency_cleanup=emergency_cleanup)
