"""
Unit tests for health_checker module
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skill', 'scripts'))

from health_checker import (
    HealthIssue,
    HealthReport,
    SessionHealthChecker,
    SessionMetrics,
    _session_ids,
    _tab_count,
    run_bsk_json,
)


def healthy_status_payload():
    return {
        "daemon_version": "0.2.3",
        "protocol_version": "1.0",
        "pid": 1234,
        "uptime_secs": 3600,
        "browsers": [
            {"instance_id": "a82b44ca", "session_count": 0, "version_skew": False}
        ],
        "sessions": ["demo"],
        "version_skew_browsers": [],
    }


class TestHelpers(unittest.TestCase):
    """Payload-shape tolerance helpers."""

    def test_session_ids_from_string_list(self):
        self.assertEqual(_session_ids({"sessions": ["a", "b"]}), ["a", "b"])

    def test_session_ids_from_object_list(self):
        payload = {"sessions": [{"session_id": "x"}, {"id": "y"}, {}]}
        self.assertEqual(_session_ids(payload), ["x", "y"])

    def test_tab_count_from_list(self):
        self.assertEqual(_tab_count([{}, {}, {}]), 3)

    def test_tab_count_from_dict(self):
        self.assertEqual(_tab_count({"tabs": [{}, {}]}), 2)

    def test_tab_count_unknown_shape(self):
        self.assertIsNone(_tab_count("weird"))


class TestHealthCheckerEnvironment(unittest.TestCase):
    """Environment-level checks (no --session)."""

    def test_healthy_environment(self):
        checker = SessionHealthChecker(
            status_probe=lambda: (healthy_status_payload(), None, 0.1)
        )
        report = checker.check()
        self.assertEqual(report.status, "healthy")
        self.assertEqual(report.issues, [])
        self.assertEqual(report.metrics.daemon_version, "0.2.3")
        self.assertEqual(report.metrics.connected_browsers, 1)
        self.assertEqual(report.metrics.active_sessions, 1)
        self.assertIn("All checks passed.", report.recovery_suggestions)

    def test_daemon_unreachable_is_unhealthy(self):
        checker = SessionHealthChecker(
            status_probe=lambda: (None, "connection refused", 0.01)
        )
        report = checker.check()
        self.assertEqual(report.status, "unhealthy")
        self.assertEqual(report.issues[0].severity, "fatal")
        self.assertEqual(report.issues[0].category, "connectivity")
        self.assertIn("doctor.py", " ".join(report.recovery_suggestions))

    def test_no_connected_browser_is_critical(self):
        payload = healthy_status_payload()
        payload["browsers"] = []
        checker = SessionHealthChecker(status_probe=lambda: (payload, None, 0.1))
        report = checker.check()
        self.assertEqual(report.status, "unhealthy")
        self.assertTrue(
            any(issue.category == "connectivity" and issue.severity == "critical"
                for issue in report.issues)
        )

    def test_version_skew_is_critical(self):
        payload = healthy_status_payload()
        payload["version_skew_browsers"] = [{"instance_id": "x"}]
        checker = SessionHealthChecker(status_probe=lambda: (payload, None, 0.1))
        report = checker.check()
        self.assertEqual(report.status, "unhealthy")
        self.assertEqual(report.metrics.version_skew_browsers, 1)

    def test_high_latency_is_degraded(self):
        checker = SessionHealthChecker(
            status_probe=lambda: (healthy_status_payload(), None, 6.2)
        )
        report = checker.check()
        self.assertEqual(report.status, "degraded")
        self.assertTrue(any(issue.category == "latency" for issue in report.issues))
        self.assertGreater(report.metrics.daemon_latency_ms, 5000)

    def test_recent_daemon_restart_is_warning(self):
        payload = healthy_status_payload()
        payload["uptime_secs"] = 5
        checker = SessionHealthChecker(status_probe=lambda: (payload, None, 0.1))
        report = checker.check()
        self.assertEqual(report.status, "degraded")

    def test_unexpected_payload_shape(self):
        checker = SessionHealthChecker(status_probe=lambda: ("not-a-dict", None, 0.1))
        report = checker.check()
        self.assertEqual(report.status, "unhealthy")
        self.assertEqual(report.issues[0].severity, "critical")


class TestHealthCheckerSession(unittest.TestCase):
    """Session-level checks (--session <id>)."""

    def test_active_session_with_tabs_is_healthy(self):
        checker = SessionHealthChecker(
            status_probe=lambda: (healthy_status_payload(), None, 0.1),
            tabs_probe=lambda sid: ([{"tab_id": 1}, {"tab_id": 2}], None, 0.1),
        )
        report = checker.check("demo")
        self.assertEqual(report.status, "healthy")
        self.assertEqual(report.metrics.session_tab_count, 2)

    def test_missing_session_is_fatal(self):
        checker = SessionHealthChecker(
            status_probe=lambda: (healthy_status_payload(), None, 0.1),
        )
        report = checker.check("gone")
        self.assertEqual(report.status, "unhealthy")
        self.assertEqual(report.issues[0].severity, "fatal")
        self.assertEqual(report.issues[0].category, "session_state")

    def test_tab_probe_failure_is_critical(self):
        checker = SessionHealthChecker(
            status_probe=lambda: (healthy_status_payload(), None, 0.1),
            tabs_probe=lambda sid: (None, "tab list failed", 0.1),
        )
        report = checker.check("demo")
        self.assertEqual(report.status, "unhealthy")
        self.assertTrue(any(issue.severity == "critical" for issue in report.issues))

    def test_zero_tabs_is_zombie_warning(self):
        checker = SessionHealthChecker(
            status_probe=lambda: (healthy_status_payload(), None, 0.1),
            tabs_probe=lambda sid: ([], None, 0.1),
        )
        report = checker.check("demo")
        self.assertEqual(report.status, "degraded")
        self.assertEqual(report.metrics.session_tab_count, 0)
        self.assertTrue(any("zombie" in issue.message for issue in report.issues))


class TestRecovery(unittest.TestCase):
    """Recovery action dispatch."""

    def test_recover_runs_command_with_session(self):
        captured = []

        def fake_runner(bsk_args):
            captured.extend(bsk_args)
            return 0

        checker = SessionHealthChecker(recovery_runner=fake_runner)
        issue = HealthIssue(
            severity="warning",
            category="session_state",
            message="tab stuck",
            auto_recoverable=True,
            recovery_command=["reload"],
        )
        self.assertTrue(checker.recover("demo", issue))
        self.assertEqual(captured, ["reload", "--session", "demo"])

    def test_recover_refuses_non_recoverable(self):
        checker = SessionHealthChecker(recovery_runner=lambda args: 0)
        issue = HealthIssue(
            severity="fatal",
            category="session_state",
            message="session gone",
            auto_recoverable=False,
        )
        self.assertFalse(checker.recover("demo", issue))

    def test_recover_reports_command_failure(self):
        checker = SessionHealthChecker(recovery_runner=lambda args: 1)
        issue = HealthIssue(
            severity="warning",
            category="session_state",
            message="tab stuck",
            auto_recoverable=True,
            recovery_command=["reload"],
        )
        self.assertFalse(checker.recover("demo", issue))


class TestSerialization(unittest.TestCase):
    """Report serialization shape."""

    def test_report_to_dict_structure(self):
        checker = SessionHealthChecker(
            status_probe=lambda: (healthy_status_payload(), None, 0.1),
            tabs_probe=lambda sid: ([{}], None, 0.1),
        )
        payload = checker.check("demo").to_dict()
        for key in ("status", "issues", "metrics", "recovery_suggestions"):
            self.assertIn(key, payload)
        for key in ("daemon_latency_ms", "daemon_version", "connected_browsers",
                    "version_skew_browsers", "active_sessions", "session_tab_count"):
            self.assertIn(key, payload["metrics"])

    def test_issue_to_dict_structure(self):
        issue = HealthIssue("warning", "latency", "slow", False, ["reload"])
        payload = issue.to_dict()
        self.assertEqual(payload["severity"], "warning")
        self.assertEqual(payload["recovery_command"], ["reload"])


if __name__ == "__main__":
    unittest.main()
