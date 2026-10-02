"""Tests for scripts/upstream_sync.py triage helpers (pure functions only)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import upstream_sync as sync  # noqa: E402


class FrozenPathTest(unittest.TestCase):
    def test_remote_daemon_paths_are_never_portable(self):
        files = [
            "crates/bsk-cli/src/daemon/remote/mod.rs",
            "crates/bsk-cli/src/daemon/ws.rs",
        ]
        info = sync.classify_files(files, set())
        self.assertEqual(info["frozen"], 1)
        self.assertEqual(info["files"], 2)

    def test_remote_extension_and_tests_are_frozen(self):
        for path in (
            "apps/extension/src/transport/remote-endpoint.ts",
            "docs/remote-extension-connection.md",
            "crates/bsk-cli/tests/remote_server.rs",
        ):
            self.assertEqual(sync.classify_files([path], set())["frozen"], 1)

    def test_overlap_counts_files_we_also_changed(self):
        ours = {"apps/extension/src/entrypoints/popup/App.tsx"}
        files = ["apps/extension/src/entrypoints/popup/App.tsx", "apps/extension/src/tools/dispatcher.ts"]
        info = sync.classify_files(files, ours)
        self.assertEqual(info["overlap"], 1)
        self.assertEqual(info["overlap_files"], ["apps/extension/src/entrypoints/popup/App.tsx"])


class RenderTest(unittest.TestCase):
    ROW = {
        "hash": "abc1234",
        "date": "2026-10-02",
        "subject": "fix(extension): something",
        "ported": False,
        "files": 3,
        "frozen": 0,
        "overlap": 1,
        "overlap_files": [],
    }

    def test_plain_output_skips_already_ported(self):
        ported = dict(self.ROW, ported=True)
        out = sync.render_triage([self.ROW, ported], markdown=False)
        self.assertIn("pending=1 already-ported=1 total=2", out)
        self.assertIn("abc1234", out)

    def test_markdown_table_has_header(self):
        out = sync.render_triage([self.ROW], markdown=True)
        self.assertTrue(out.splitlines()[2].startswith("| Commit | Date |"))
        self.assertIn("| `abc1234` | 2026-10-02 | 3 | 0 | 1 |", out)

    def test_table_renders_missing_upstream_hash(self):
        out = sync.render_table_rows([("fedcba9", "", "fix: thing")])
        self.assertIn("| `—` | `fedcba9` | fix: thing |", out)


class UpstreamHashTest(unittest.TestCase):
    BODY = "\n".join(
        [
            "fix(extension): bound the thing",
            "",
            "Explain the fix.",
            "",
            "(cherry picked from commit d247cb7895adada9e98905b37b1d5d34f16d43fc)",
            "",
        ]
    )

    def test_extracts_short_upstream_hash(self):
        self.assertEqual(sync.upstream_of_body(self.BODY), "d247cb7")

    def test_returns_empty_without_marker(self):
        self.assertEqual(sync.upstream_of_body("chore: our own commit\n"), "")


if __name__ == "__main__":
    unittest.main()
