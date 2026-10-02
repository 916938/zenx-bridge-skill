#!/usr/bin/env python3
"""
Session health monitoring and auto-recovery for ZenX Bridge Skill v1.1.0

Proactive session health assessment built on `bsk status --json`:
- Daemon / extension connectivity (no connected browser, daemon unreachable)
- Session liveness (target session present in the daemon's session list)
- Version-skew detection across connected browsers (exit-code-5 class issues)
- Daemon latency measurement (degraded beyond the warning threshold)
- Zombie-session detection (active session reporting zero tabs)
- Automatic recovery for recoverable issues (e.g. tab reload)

Environment-level readiness (daemon, port, extension) is covered by
doctor.py; this module layers session-aware checks on top of it and its
suggestions point back to doctor.py when the environment is the problem.
"""

import argparse
import json
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from bsk_client import configure_utf8_output

# Severity -> overall status contribution
ISSUE_SEVERITY_STATUS = {
    "warning": "degraded",
    "critical": "unhealthy",
    "fatal": "unhealthy",
}

# Latency beyond this (seconds) marks the daemon as degraded
LATENCY_WARNING_SECS = 5.0

# Daemon uptime below this (seconds) suggests a crash-restart cycle
RECENT_RESTART_WARNING_SECS = 10.0


@dataclass(frozen=True)
class HealthIssue:
    """
    A single detected health problem.

    Attributes:
        severity: "warning" (degraded), "critical"/"fatal" (unhealthy)
        category: connectivity | session_state | version_skew | latency
        message: Human-readable description
        auto_recoverable: Whether recover() may attempt an automatic fix
        recovery_command: bsk args (without --session) used for recovery
    """

    severity: str
    category: str
    message: str
    auto_recoverable: bool
    recovery_command: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "auto_recoverable": self.auto_recoverable,
            "recovery_command": self.recovery_command,
        }


@dataclass
class SessionMetrics:
    """Quantitative snapshot accompanying a HealthReport."""

    daemon_latency_ms: Optional[float] = None
    daemon_version: Optional[str] = None
    daemon_uptime_secs: Optional[int] = None
    connected_browsers: int = 0
    version_skew_browsers: int = 0
    active_sessions: int = 0
    session_tab_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "daemon_latency_ms": self.daemon_latency_ms,
            "daemon_version": self.daemon_version,
            "daemon_uptime_secs": self.daemon_uptime_secs,
            "connected_browsers": self.connected_browsers,
            "version_skew_browsers": self.version_skew_browsers,
            "active_sessions": self.active_sessions,
            "session_tab_count": self.session_tab_count,
        }


@dataclass
class HealthReport:
    """Overall assessment: status, issues, metrics, and suggestions."""

    status: str  # healthy | degraded | unhealthy
    issues: List[HealthIssue] = field(default_factory=list)
    metrics: SessionMetrics = field(default_factory=SessionMetrics)
    recovery_suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "issues": [issue.to_dict() for issue in self.issues],
            "metrics": self.metrics.to_dict(),
            "recovery_suggestions": self.recovery_suggestions,
        }


def run_bsk_json(args: List[str]) -> Tuple[Optional[Any], Optional[str], float]:
    """
    Run `bsk <args...> --json` and return (parsed, error, elapsed_seconds).

    The command never raises: failures come back as (None, message, elapsed).
    """
    start = time.monotonic()
    try:
        result = subprocess.run(
            ["bsk", *args, "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        return None, str(error), time.monotonic() - start
    elapsed = time.monotonic() - start

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return None, detail or f"exit code {result.returncode}", elapsed
    try:
        return json.loads(result.stdout), None, elapsed
    except json.JSONDecodeError as error:
        return None, f"invalid JSON output: {error}", elapsed


def _session_ids(status: Dict[str, Any]) -> List[str]:
    """Extract session ids from a `bsk status` payload, tolerating shapes."""
    ids: List[str] = []
    for entry in status.get("sessions") or []:
        if isinstance(entry, str):
            ids.append(entry)
        elif isinstance(entry, dict):
            ids.append(str(entry.get("session_id") or entry.get("id") or ""))
    return [sid for sid in ids if sid]


def _tab_count(tabs_payload: Any) -> Optional[int]:
    """Count tabs from a `bsk tab list` payload (list or {"tabs": [...]}})."""
    if isinstance(tabs_payload, list):
        return len(tabs_payload)
    if isinstance(tabs_payload, dict):
        tabs = tabs_payload.get("tabs")
        if isinstance(tabs, list):
            return len(tabs)
    return None


class SessionHealthChecker:
    """
    Assess BrowserSkill session health and attempt automatic recovery.

    Probes are injectable for testing; production probes shell out to the
    bsk CLI. Each probe returns (data, error, elapsed_seconds).
    """

    def __init__(
        self,
        status_probe: Optional[Callable[[], Tuple[Optional[Any], Optional[str], float]]] = None,
        tabs_probe: Optional[Callable[[str], Tuple[Optional[Any], Optional[str], float]]] = None,
        recovery_runner: Optional[Callable[[List[str]], int]] = None,
    ):
        self._status_probe = status_probe or (lambda: run_bsk_json(["status"]))
        self._tabs_probe = tabs_probe or (
            lambda session_id: run_bsk_json(["tab", "list", "--session", session_id])
        )
        self._recovery_runner = recovery_runner or self._default_recovery_runner

    @staticmethod
    def _default_recovery_runner(bsk_args: List[str]) -> int:
        result = subprocess.run(
            ["bsk", *bsk_args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode

    # ------------------------------------------------------------------ check

    def check(self, session_id: Optional[str] = None) -> HealthReport:
        """
        Run all health checks.

        Args:
            session_id: Optional target session. When given, session-level
                checks (liveness, tabs) run in addition to environment checks.
        """
        issues: List[HealthIssue] = []
        suggestions: List[str] = []
        metrics = SessionMetrics()

        status, error, latency = self._status_probe()
        metrics.daemon_latency_ms = round(latency * 1000, 1)

        if status is None:
            issues.append(
                HealthIssue(
                    severity="fatal",
                    category="connectivity",
                    message=f"bsk status failed: {error}",
                    auto_recoverable=False,
                )
            )
            suggestions.append("Run scripts/doctor.py to diagnose daemon and extension readiness.")
            return HealthReport("unhealthy", issues, metrics, suggestions)

        if not isinstance(status, dict):
            issues.append(
                HealthIssue(
                    severity="critical",
                    category="connectivity",
                    message="bsk status returned an unexpected payload shape",
                    auto_recoverable=False,
                )
            )
            return HealthReport("unhealthy", issues, metrics, suggestions)

        metrics.daemon_version = status.get("daemon_version")
        uptime = status.get("uptime_secs")
        metrics.daemon_uptime_secs = uptime if isinstance(uptime, int) else None
        browsers = status.get("browsers") or []
        metrics.connected_browsers = len(browsers)
        skew = status.get("version_skew_browsers") or []
        metrics.version_skew_browsers = len(skew)
        session_ids = _session_ids(status)
        metrics.active_sessions = len(session_ids)

        # Environment-level issues
        if not browsers:
            issues.append(
                HealthIssue(
                    severity="critical",
                    category="connectivity",
                    message="No connected browser: the extension is not attached to the daemon",
                    auto_recoverable=False,
                )
            )
            suggestions.append("Open the browser and confirm the BrowserSkill extension is enabled.")

        if skew:
            issues.append(
                HealthIssue(
                    severity="critical",
                    category="version_skew",
                    message=f"{len(skew)} browser(s) report CLI/extension version skew",
                    auto_recoverable=False,
                )
            )
            suggestions.append("Upgrade the bsk CLI and extension to matching versions (exit code 5).")

        if metrics.daemon_uptime_secs is not None and metrics.daemon_uptime_secs < RECENT_RESTART_WARNING_SECS:
            issues.append(
                HealthIssue(
                    severity="warning",
                    category="connectivity",
                    message=f"Daemon restarted recently (uptime {metrics.daemon_uptime_secs}s)",
                    auto_recoverable=False,
                )
            )
            suggestions.append("If this was unexpected, inspect daemon logs with 'bsk logs'.")

        if latency > LATENCY_WARNING_SECS:
            issues.append(
                HealthIssue(
                    severity="warning",
                    category="latency",
                    message=f"Daemon responded in {latency:.1f}s (threshold {LATENCY_WARNING_SECS:.0f}s)",
                    auto_recoverable=False,
                )
            )
            suggestions.append("Check daemon load with 'bsk status' before issuing further commands.")

        # Session-level issues
        if session_id is not None:
            if session_id not in session_ids:
                issues.append(
                    HealthIssue(
                        severity="fatal",
                        category="session_state",
                        message=f"Session '{session_id}' is not active (idle-timeout or already stopped)",
                        auto_recoverable=False,
                    )
                )
                suggestions.append("Start a new session with 'bsk session start' and re-run the task.")
            else:
                tabs, tab_error, _ = self._tabs_probe(session_id)
                if tabs is None:
                    issues.append(
                        HealthIssue(
                            severity="critical",
                            category="session_state",
                            message=f"Tab list for session '{session_id}' failed: {tab_error}",
                            auto_recoverable=False,
                        )
                    )
                    suggestions.append("Re-check the session with 'bsk tab list --session <id>'.")
                else:
                    count = _tab_count(tabs)
                    metrics.session_tab_count = count
                    if count == 0:
                        issues.append(
                            HealthIssue(
                                severity="warning",
                                category="session_state",
                                message=f"Session '{session_id}' has no tabs (zombie session)",
                                auto_recoverable=False,
                            )
                        )
                        suggestions.append("Stop the zombie session with 'bsk session stop <id>' and start a new one.")

        report = HealthReport(
            status=self._overall_status(issues),
            issues=issues,
            metrics=metrics,
            recovery_suggestions=suggestions,
        )
        if report.status == "healthy" and not suggestions:
            suggestions.append("All checks passed.")
        return report

    @staticmethod
    def _overall_status(issues: List[HealthIssue]) -> str:
        status = "healthy"
        for issue in issues:
            contributed = ISSUE_SEVERITY_STATUS.get(issue.severity)
            if contributed == "unhealthy":
                return "unhealthy"
            if contributed == "degraded":
                status = "degraded"
        return status

    # ---------------------------------------------------------------- recover

    def recover(self, session_id: str, issue: HealthIssue) -> bool:
        """
        Attempt the automatic recovery action for an issue.

        Returns True when the recovery command ran and exited 0.
        Issues without a recovery_command or with auto_recoverable=False
        always return False.
        """
        if not issue.auto_recoverable or not issue.recovery_command:
            return False
        bsk_args = [*issue.recovery_command]
        if session_id:
            bsk_args.extend(["--session", session_id])
        return self._recovery_runner(bsk_args) == 0

    def check_and_recover(self, session_id: str, auto: bool = False) -> HealthReport:
        """Convenience wrapper: check, then recover every recoverable issue."""
        report = self.check(session_id)
        if not auto:
            return report
        for issue in list(report.issues):
            if issue.auto_recoverable:
                self.recover(session_id, issue)
        return report


# ------------------------------------------------------------------------- CLI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assess BrowserSkill session health (read-only unless --auto)."
    )
    parser.add_argument("--session", help="Target session id for session-level checks.")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Attempt automatic recovery for recoverable issues.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Compatibility flag; output is always JSON.",
    )
    return parser.parse_args()


def main() -> None:
    configure_utf8_output()
    args = parse_args()
    checker = SessionHealthChecker()
    report = checker.check_and_recover(args.session, auto=args.auto)
    payload = report.to_dict()
    if args.auto:
        payload["auto_recovery"] = True
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report.status == "healthy" else 1)


if __name__ == "__main__":
    main()
