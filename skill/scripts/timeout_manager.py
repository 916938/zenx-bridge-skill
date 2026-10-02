"""
Timeout management and signal handling system for ZenX Bridge Skill v1.1.0

Implements a layered timeout architecture:
- Connect timeout: 10s (daemon connection)
- Command timeout: 30s (single bsk command)
- Session timeout: 300s (entire session lifetime)
- Global timeout: 600s (absolute maximum)

Also provides:
- Signal handling (SIGINT, SIGTERM) for graceful cancellation
- Timeout context managers
- Cancellation token pattern for cooperative cancellation
"""

import signal
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from error_codes import TIMEOUT, CANCELLED


class TimeoutLayer(Enum):
    """Timeout layer identifiers."""

    CONNECT = "CONNECT"           # Daemon connection establishment
    COMMAND = "COMMAND"           # Single bsk command execution
    SESSION = "SESSION"           # Browser session lifetime
    GLOBAL = "GLOBAL"             # Absolute upper bound


@dataclass
class TimeoutConfig:
    """
    Configuration for all timeout layers.

    Attributes:
        connect_timeout: Max time to establish daemon connection (default: 10s)
        command_timeout: Max time for single command execution (default: 30s)
        session_timeout: Max session idle/total time (default: 300s = 5min)
        global_timeout: Absolute maximum operation time (default: 600s = 10min)
        enable_signal_handling: Whether to install SIGINT/SIGTERM handlers
    """

    connect_timeout: float = 10.0
    command_timeout: float = 30.0
    session_timeout: float = 300.0
    global_timeout: float = 600.0
    enable_signal_handling: bool = True


@dataclass
class TimeoutResult:
    """
    Result of a timed operation.

    Attributes:
        completed: Whether the operation completed normally
        timed_out: Whether it was terminated due to timeout
        cancelled: Whether it was cancelled by user/signal
        duration: How long the operation ran
        layer: Which timeout layer triggered (if applicable)
        result: Return value if successful
        error: Exception if failed
    """

    completed: bool = False
    timed_out: bool = False
    cancelled: bool = False
    duration: float = 0.0
    layer: Optional[TimeoutLayer] = None
    result: Any = None
    error: Optional[Exception] = None

    @property
    def is_success(self) -> bool:
        return self.completed and not self.timed_out and not self.cancelled

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.is_success,
            "completed": self.completed,
            "timed_out": self.timed_out,
            "cancelled": self.cancelled,
            "duration_s": round(self.duration, 3),
            "layer": self.layer.value if self.layer else None,
        }


class CancellationToken:
    """
    Cooperative cancellation token.

    Long-running operations can check this token periodically
    and exit gracefully if cancellation is requested.

    Usage:
        token = CancellationToken()

        def long_operation():
            for item in items:
                if token.is_cancelled:
                    raise OperationCancelled()
                process(item)
    """

    def __init__(self):
        self._cancelled = False
        self._reason: Optional[str] = None
        self._lock = threading.Lock()

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        with self._lock:
            return self._cancelled

    @property
    def reason(self) -> Optional[str]:
        """Get reason for cancellation."""
        with self._lock:
            return self._reason

    def cancel(self, reason: str = "User requested cancellation"):
        """Request cancellation."""
        with self._lock:
            self._cancelled = True
            self._reason = reason

    def reset(self):
        """Reset cancellation state (for reuse)."""
        with self._lock:
            self._cancelled = False
            self._reason = None

    def raise_if_cancelled(self):
        """Raise CancelledError if cancellation was requested."""
        if self.is_cancelled:
            raise OperationCancelled(self.reason)


class OperationCancelled(Exception):
    """Raised when an operation is cancelled via CancellationToken."""

    def __init__(self, reason: Optional[str] = None):
        self.reason = reason
        super().__init__(f"Operation cancelled: {reason}" if reason else "Operation cancelled")


class TimeoutManager:
    """
    Centralized timeout and cancellation management.

    Usage:
        manager = TimeoutManager(TimeoutConfig())

        # Using context manager
        with manager.timeout_context(TimeoutLayer.COMMAND):
            result = slow_function()

        # With explicit control
        result_obj = manager.execute_with_timeout(
            my_func,
            timeout_layer=TimeoutLayer.COMMAND,
            args=(arg1,),
            kwargs={"key": value},
        )

        if result_obj.timed_out:
            print("Operation timed out!")
    """

    def __init__(self, config: Optional[TimeoutConfig] = None):
        self.config = config or TimeoutConfig()
        self._cancellation_token = CancellationToken()
        self._original_handlers: Dict[int, Any] = {}
        self._start_time: float = time.time()  # Initialize at creation

        if self.config.enable_signal_handling:
            self._install_signal_handlers()

    def _install_signal_handlers(self):
        """Install SIGINT/SIGTERM handlers for graceful shutdown."""
        try:
            self._original_handlers[signal.SIGINT] = signal.signal(
                signal.SIGINT,
                self._signal_handler,
            )
            self._original_handlers[signal.SIGTERM] = signal.signal(
                signal.SIGTERM,
                self._signal_handler,
            )
        except (ValueError, OSError):
            # Signal handling not available (e.g., Windows threads)
            pass

    def _uninstall_signal_handlers(self):
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass
        self._original_handlers.clear()

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals."""
        self._cancellation_token.cancel(
            f"Received signal {signum}"
        )

    @property
    def cancellation_token(self) -> CancellationToken:
        """Get the shared cancellation token."""
        return self._cancellation_token

    def get_timeout_for_layer(self, layer: TimeoutLayer) -> float:
        """Get configured timeout for a specific layer."""
        timeouts = {
            TimeoutLayer.CONNECT: self.config.connect_timeout,
            TimeoutLayer.COMMAND: self.config.command_timeout,
            TimeoutLayer.SESSION: self.config.session_timeout,
            TimeoutLayer.GLOBAL: self.config.global_timeout,
        }
        return timeouts.get(layer, self.config.command_timeout)

    @contextmanager
    def timeout_context(
        self,
        layer: TimeoutLayer = TimeoutLayer.COMMAND,
        custom_timeout: Optional[float] = None,
    ):
        """
        Context manager for automatic timeout enforcement.

        Usage:
            with manager.timeout_context(TimeoutLayer.COMMAND):
                do_something()

            If the block takes too long, TimeoutError is raised.
        """
        timeout = custom_timeout or self.get_timeout_for_layer(layer)
        start_time = time.time()

        # Check global elapsed time
        global_elapsed = time.time() - self._start_time
        remaining_global = self.config.global_timeout - global_elapsed
        if remaining_global <= 0:
            return TimeoutResult(
                completed=False,
                timed_out=True,
                duration=global_elapsed,
                layer=TimeoutLayer.GLOBAL,
                error=TimeoutError(f"Global timeout exceeded ({self.config.global_timeout}s)"),
            )
        # Use the smaller of layer timeout or remaining global time
        effective_timeout = min(timeout, remaining_global)

        # Check cancellation before starting
        self._cancellation_token.raise_if_cancelled()

        yield

        # After block completes, check duration
        elapsed = time.time() - start_time
        if elapsed > effective_timeout:
            raise TimeoutError(
                f"Operation exceeded {layer.value} timeout "
                f"({elapsed:.2f}s > {effective_timeout:.2f}s)"
            )

    def execute_with_timeout(
        self,
        func: Callable[..., Any],
        *args,
        timeout_layer: TimeoutLayer = TimeoutLayer.COMMAND,
        custom_timeout: Optional[float] = None,
        **kwargs,
    ) -> TimeoutResult:
        """
        Execute function with timeout and cancellation support.

        Args:
            func: Function to call
            *args, **kwargs: Arguments to forward
            timeout_layer: Which timeout layer to apply
            custom_timeout: Override default timeout for this layer

        Returns:
            TimeoutResult with outcome details
        """
        timeout = custom_timeout or self.get_timeout_for_layer(timeout_layer)
        start_time = time.time()

        # Track global start time
        if self._start_time is None:
            self._start_time = time.time()

        try:
            # Execute in a separate thread to allow timeout enforcement
            result_container = [None]
            exception_container = [None]

            def target():
                try:
                    result_container[0] = func(*args, **kwargs)
                except Exception as e:
                    exception_container[0] = e

            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout=timeout)

            if thread.is_alive():
                # Thread didn't finish in time
                duration = time.time() - start_time
                return TimeoutResult(
                    completed=False,
                    timed_out=True,
                    duration=duration,
                    layer=timeout_layer,
                    error=TimeoutError(f"{timeout_layer.value} timeout after {timeout}s"),
                )

            # Thread completed
            if exception_container[0]:
                raise exception_container[0]

            duration = time.time() - start_time
            return TimeoutResult(
                completed=True,
                duration=duration,
                layer=timeout_layer,
                result=result_container[0],
            )

        except OperationCancelled as e:
            duration = time.time() - start_time
            return TimeoutResult(
                completed=False,
                cancelled=True,
                duration=duration,
                error=e,
            )
        except Exception as e:
            duration = time.time() - start_time
            return TimeoutResult(
                completed=False,
                duration=duration,
                error=e,
            )

    def check_global_timeout(self) -> bool:
        """Check if global timeout has been exceeded."""
        elapsed = time.time() - self._start_time
        return elapsed >= self.config.global_timeout

    def get_elapsed_time(self) -> float:
        """Get total elapsed time since manager creation/reset."""
        return time.time() - self._start_time

    def reset_global_timer(self):
        """Reset the global timeout timer."""
        self._start_time = time.time()

    def cleanup(self):
        """Clean up resources (restore signal handlers)."""
        self._uninstall_signal_handlers()
        self._cancellation_token.reset()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False


# Convenience functions for quick usage
def run_with_timeout(
    func: Callable[..., Any],
    timeout_seconds: float,
    *args,
    **kwargs,
) -> Tuple[Any, bool]:
    """
    Quick timeout wrapper for simple use cases.

    Usage:
        result, completed = run_with_timeout(slow_func, 5.0, arg1, arg2)
        if not completed:
            print("Timed out!")

    Returns:
        Tuple of (result_or_None, completed_successfully)
    """
    manager = TimeoutManager(TimeoutConfig(enable_signal_handling=False))
    result = manager.execute_with_timeout(
        func,
        *args,
        timeout_layer=TimeoutLayer.COMMAND,
        custom_timeout=timeout_seconds,
        **kwargs,
    )
    return (result.result, result.completed)


def create_cancellation_token() -> CancellationToken:
    """Create a new isolated cancellation token."""
    return CancellationToken()


@contextmanager
def command_timeout(seconds: float):
    """Quick context manager for command-level timeout."""
    manager = TimeoutManager(TimeoutConfig(enable_signal_handling=False))
    with manager.timeout_context(TimeoutLayer.COMMAND, custom_timeout=seconds):
        yield manager.cancellation_token
