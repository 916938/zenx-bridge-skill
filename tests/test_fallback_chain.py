"""
Unit tests for fallback_chain module
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skill', 'scripts'))

from fallback_chain import (
    AttemptRecord,
    FallbackChain,
    FallbackConfig,
    FallbackLevel,
    FallbackResult,
    LevelSpec,
    default_chain,
    should_fallback,
    strip_optional_args,
)
from error_codes import (
    TIMEOUT,
    CONNECTION_LOST,
    INVALID_PARAMS,
    AUTH_FAILED,
    SESSION_EXPIRED,
    INTERNAL_ERROR,
    VALIDATION_FAILED,
)


class FlakyExecutor:
    """Executor that fails N times with given exceptions, then succeeds."""

    def __init__(self, failures, value="ok"):
        self.failures = list(failures)
        self.value = value
        self.calls = []

    def __call__(self, action, args, session):
        self.calls.append((action, dict(args), session))
        if self.failures:
            raise self.failures.pop(0)
        return self.value


class TestShouldFallback(unittest.TestCase):
    """Error-category escalation rules."""

    def test_transient_errors_fall_through(self):
        self.assertTrue(should_fallback(TIMEOUT))
        self.assertTrue(should_fallback(CONNECTION_LOST))

    def test_system_errors_fall_through(self):
        self.assertTrue(should_fallback(INTERNAL_ERROR))

    def test_param_errors_fall_through(self):
        self.assertTrue(should_fallback(INVALID_PARAMS))
        self.assertTrue(should_fallback(VALIDATION_FAILED))

    def test_other_permanent_errors_stop(self):
        self.assertFalse(should_fallback(AUTH_FAILED))

    def test_user_errors_stop(self):
        self.assertFalse(should_fallback(SESSION_EXPIRED))


class TestStripOptionalArgs(unittest.TestCase):
    """Simplified-argument reduction."""

    def test_keeps_only_required_keys(self):
        args = {"selector": "@e1", "value": "x", "timeout": 30, "mode": "drop"}
        self.assertEqual(strip_optional_args(args, ["selector", "value"]),
                         {"selector": "@e1", "value": "x"})

    def test_empty_required_keeps_nothing(self):
        self.assertEqual(strip_optional_args({"a": 1}, []), {})

    def test_no_required_list_returns_empty(self):
        self.assertEqual(strip_optional_args({"a": 1}, None), {})


class TestFallbackChainExecution(unittest.TestCase):
    """Core degradation behaviour."""

    def _chain(self, passthrough, legacy, config=None, **kwargs):
        return default_chain(
            passthrough,
            legacy,
            config=config,
            required_keys=["selector", "value"],
            **kwargs,
        )

    def test_first_level_success(self):
        result = self._chain(FlakyExecutor([]), FlakyExecutor([])).execute(
            "fill", {"selector": "@e1", "value": "x"}, "demo"
        )
        self.assertTrue(result.succeeded)
        self.assertEqual(result.value, "ok")
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(result.attempts[0].mode, "passthrough")
        self.assertEqual(result.attempts[0].status, "success")
        self.assertFalse(result.used_fallback)

    def test_fallback_to_legacy(self):
        chain = self._chain(
            FlakyExecutor([TimeoutError("daemon busy")]),
            FlakyExecutor([]),
        )
        result = chain.execute("fill", {"selector": "@e1", "value": "x"}, "demo")
        self.assertTrue(result.succeeded)
        self.assertEqual([a.status for a in result.attempts], ["failed", "success"])
        self.assertEqual(result.attempts[0].next_action, "fallback_to_legacy")
        self.assertTrue(result.used_fallback)

    def test_fallback_to_simplified(self):
        bad_params = ValueError("unsupported argument shape")
        # The simplified level reuses the legacy executor, so the legacy
        # failure queue only needs one entry: it fails once, then the
        # simplified retry (same executor) succeeds.
        chain = self._chain(
            FlakyExecutor([bad_params]),
            FlakyExecutor([bad_params]),
        )
        result = chain.execute("fill", {"selector": "@e1", "value": "x", "timeout": 5}, "demo")
        self.assertTrue(result.succeeded)
        self.assertEqual([a.mode for a in result.attempts],
                         ["passthrough", "legacy", "simplified"])
        self.assertEqual([a.status for a in result.attempts],
                         ["failed", "failed", "success"])

    def test_simplified_level_strips_optional_args(self):
        legacy = FlakyExecutor([ValueError("too many args")])
        chain = self._chain(
            FlakyExecutor([ValueError("invoke unavailable")]),
            legacy,
        )
        # legacy fails once with full args, then succeeds on the simplified retry
        result = chain.execute(
            "fill", {"selector": "@e1", "value": "x", "timeout": 99}, "demo"
        )
        self.assertTrue(result.succeeded)
        simplified_call = legacy.calls[-1][1]
        self.assertNotIn("timeout", simplified_call)
        self.assertIn("timeout", legacy.calls[0][1])

    def test_all_levels_fail_returns_structured_error(self):
        error = TimeoutError("always down")
        chain = self._chain(
            FlakyExecutor([error, error, error, error]),
            FlakyExecutor([error, error]),
        )
        result = chain.execute("fill", {"selector": "@e1"}, "demo")
        self.assertFalse(result.succeeded)
        self.assertIsNotNone(result.final_error)
        self.assertEqual(result.final_error.code, "TIMEOUT")
        self.assertEqual(result.attempts[-1].next_action, "give_up")

    def test_permanent_error_stops_immediately(self):
        chain = self._chain(
            FlakyExecutor([PermissionError("denied")]),
            FlakyExecutor([]),
        )
        result = chain.execute("fill", {"selector": "@e1"}, "demo")
        self.assertFalse(result.succeeded)
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(result.attempts[0].next_action, "stop")

    def test_disabled_fallback_stops_after_first_level(self):
        chain = self._chain(
            FlakyExecutor([TimeoutError("boom")]),
            FlakyExecutor([]),
            config=FallbackConfig(enabled=False),
        )
        result = chain.execute("fill", {"selector": "@e1"}, "demo")
        self.assertFalse(result.succeeded)
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(result.attempts[0].next_action, "stop")

    def test_max_depth_limits_attempts(self):
        error = TimeoutError("slow")
        chain = self._chain(
            FlakyExecutor([error, error, error, error]),
            FlakyExecutor([error, error]),
            config=FallbackConfig(max_depth=2),
        )
        result = chain.execute("fill", {"selector": "@e1"}, "demo")
        self.assertFalse(result.succeeded)
        executed = [a for a in result.attempts if a.status == "failed"]
        skipped = [a for a in result.attempts if a.status == "skipped"]
        self.assertEqual(len(executed), 2)
        self.assertTrue(any("max fallback depth" in (a.error or "") for a in skipped))

    def test_zero_depth_executes_nothing(self):
        chain = self._chain(
            FlakyExecutor([]),
            FlakyExecutor([]),
            config=FallbackConfig(max_depth=0),
        )
        result = chain.execute("fill", {"selector": "@e1"}, "demo")
        self.assertFalse(result.succeeded)
        self.assertTrue(all(a.status == "skipped" for a in result.attempts))

    def test_unavailable_level_is_skipped(self):
        chain = default_chain(
            FlakyExecutor([]),
            FlakyExecutor([]),
            passthrough_available=lambda: False,
            required_keys=["selector"],
        )
        result = chain.execute("fill", {"selector": "@e1"}, "demo")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.attempts[0].mode, "passthrough")
        self.assertEqual(result.attempts[0].status, "skipped")
        self.assertEqual(result.attempts[1].mode, "legacy")
        self.assertEqual(result.attempts[1].status, "success")


class TestDecisionLogging(unittest.TestCase):
    """Attempt record content and serialization."""

    def test_attempt_records_have_timestamps_and_durations(self):
        chain = default_chain(
            FlakyExecutor([TimeoutError("x")]),
            FlakyExecutor([]),
            required_keys=[],
        )
        result = chain.execute("fill", {}, "demo")
        for record in result.attempts:
            self.assertIsInstance(record.timestamp, str)
            self.assertGreaterEqual(len(record.timestamp), 10)
            self.assertIsInstance(record.duration_ms, float)

    def test_result_to_dict_shape(self):
        chain = default_chain(
            FlakyExecutor([]),
            FlakyExecutor([]),
            required_keys=[],
        )
        payload = chain.execute("fill", {}, "demo").to_dict()
        for key in ("succeeded", "used_fallback", "final_error", "attempts"):
            self.assertIn(key, payload)
        for key in ("mode", "status", "error", "duration_ms", "timestamp", "next_action"):
            self.assertIn(key, payload["attempts"][0])

    def test_final_error_code_serialized(self):
        chain = default_chain(
            FlakyExecutor([TimeoutError("a"), TimeoutError("b"), TimeoutError("c")]),
            FlakyExecutor([TimeoutError("d"), TimeoutError("e")]),
            required_keys=[],
        )
        result = chain.execute("fill", {}, "demo")
        self.assertEqual(result.to_dict()["final_error"], "TIMEOUT")


class TestEmergencyCleanup(unittest.TestCase):
    """Fatal-path cleanup hook."""

    def test_emergency_cleanup_runs_on_system_error(self):
        calls = []
        error = RuntimeError("daemon crashed hard")

        def cleanup(result):
            calls.append(result.final_error.code)

        chain = default_chain(
            FlakyExecutor([error, error, error]),
            FlakyExecutor([error, error]),
            required_keys=[],
            emergency_cleanup=cleanup,
        )
        result = chain.execute("fill", {}, "demo")
        self.assertFalse(result.succeeded)
        self.assertEqual(calls, ["DAEMON_CRASHED"])

    def test_no_emergency_cleanup_on_transient_exhaustion(self):
        calls = []

        chain = default_chain(
            FlakyExecutor([TimeoutError("a"), TimeoutError("b"), TimeoutError("c")]),
            FlakyExecutor([TimeoutError("d"), TimeoutError("e")]),
            required_keys=[],
            emergency_cleanup=lambda result: calls.append("ran"),
        )
        chain.execute("fill", {}, "demo")
        self.assertEqual(calls, [])

    def test_no_emergency_cleanup_on_success(self):
        calls = []
        chain = default_chain(
            FlakyExecutor([]),
            FlakyExecutor([]),
            required_keys=[],
            emergency_cleanup=lambda result: calls.append("ran"),
        )
        chain.execute("fill", {}, "demo")
        self.assertEqual(calls, [])


class TestExtensibility(unittest.TestCase):
    """Custom level registry."""

    def test_custom_levels_can_be_registered(self):
        def custom_executor(action, args, session):
            return "custom-result"

        chain = FallbackChain(
            [LevelSpec(level=FallbackLevel.LEGACY, executor=custom_executor)]
        )
        result = chain.execute("anything", {}, None)
        self.assertTrue(result.succeeded)
        self.assertEqual(result.value, "custom-result")

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            FallbackChain([])

    def test_invalid_max_depth_rejected(self):
        with self.assertRaises(ValueError):
            FallbackConfig(max_depth=-1)


if __name__ == "__main__":
    unittest.main()
