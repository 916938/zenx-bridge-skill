"""Tests for the generated command tables (command-registry.json -> SKILL.md / protocol.md)."""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "generate_command_docs.py"
REGISTRY = ROOT / "skill" / "references" / "command-registry.json"
SKILL = ROOT / "skill" / "SKILL.md"
PROTOCOL = ROOT / "skill" / "references" / "protocol.md"

sys.path.insert(0, str(ROOT / "scripts"))
import generate_command_docs as gen  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


class RegistrySchemaTest(unittest.TestCase):
    def test_registry_loads_and_validates(self):
        registry = gen.load_registry(REGISTRY)
        self.assertIn("actions", registry)
        self.assertGreater(len(registry["actions"]), 20)
        for tier in {e["tier"] for e in registry["actions"]}:
            self.assertIn(tier, registry["tiers"])

    def test_actions_are_unique(self):
        registry = gen.load_registry(REGISTRY)
        names = [e["action"] for e in registry["actions"]]
        self.assertEqual(len(names), len(set(names)))

    def test_every_block_has_actions(self):
        registry = gen.load_registry(REGISTRY)
        for block_id in gen.BLOCKS:
            owners = [e["action"] for e in registry["actions"] if block_id in e["blocks"]]
            self.assertTrue(owners, f"block '{block_id}' has no actions")

    def test_malformed_registry_is_rejected(self):
        bad_payloads = [
            '{"actions": []}',                                   # no tiers
            '{"tiers": {}, "actions": []}',                      # empty tiers / actions
            '{"tiers": {"a": "b"}, "actions": [{"action": "x"}]}',  # missing fields
            '{"tiers": {"a": "b"}, "actions": [{"action": "x", "command": "c", "tier": "zzz", "purpose": "p"}]}',
            '{"tiers": {"a": "b"}, "actions": [{"action": "x", "command": "c", "tier": "a", "purpose": "p", "blocks": ["nope"]}]}',
            '{"tiers": {"a": "b"}, "actions": [{"action": "x", "command": "c", "tier": "a", "purpose": "p"}, {"action": "x", "command": "c2", "tier": "a", "purpose": "p2"}]}',
            "not json at all",
        ]
        path = ROOT / ".bad-registry.json"
        try:
            for bad in bad_payloads:
                with self.subTest(bad=bad[:48]):
                    path.write_text(bad, encoding="utf-8")
                    with self.assertRaises(gen.RegistryError):
                        gen.load_registry(path)
        finally:
            path.unlink(missing_ok=True)

    def test_missing_registry_file_is_rejected(self):
        with self.assertRaises(gen.RegistryError):
            gen.load_registry(ROOT / ".does-not-exist.json")


class GenerationTest(unittest.TestCase):
    def test_render_is_idempotent(self):
        registry = gen.load_registry(REGISTRY)
        for block_id in gen.BLOCKS:
            first = gen.render_block(block_id, registry)
            second = gen.render_block(block_id, registry)
            self.assertEqual(first, second, f"block '{block_id}' renders differently twice")

    def test_missing_marker_raises(self):
        with self.assertRaises(gen.RegistryError):
            gen.replace_block("no markers here\n", "skill-action-map", ["- x"])

    def test_unpaired_marker_raises(self):
        text = "<!-- BEGIN GENERATED: skill-action-map -->\n| a |\n"
        with self.assertRaises(gen.RegistryError):
            gen.replace_block(text, "skill-action-map", ["- x"])

    def test_crlf_is_preserved(self):
        text = (
            "<!-- BEGIN GENERATED: skill-action-map -->\r\n"
            "| a |\r\n"
            "<!-- END GENERATED: skill-action-map -->\r\n"
        )
        out = gen.replace_block(text, "skill-action-map", ["- x"])
        self.assertIn("\r\n", out)
        self.assertNotIn("\n\n", out.replace("\r\n", "\n"))

    def test_lf_is_preserved(self):
        text = (
            "<!-- BEGIN GENERATED: skill-action-map -->\n"
            "| a |\n"
            "<!-- END GENERATED: skill-action-map -->\n"
        )
        out = gen.replace_block(text, "skill-action-map", ["- x"])
        self.assertNotIn("\r\n", out)

    def test_tables_escape_pipes_in_cells(self):
        registry = gen.load_registry(REGISTRY)
        for block_id, spec in gen.BLOCKS.items():
            if spec["style"] != "table":
                continue
            for line in gen.render_block(block_id, registry):
                if line.startswith("| ") is False:
                    continue
                cells = line.strip().strip("|").split(" | ")
                for raw in cells:
                    # A literal pipe may only appear escaped.
                    self.assertNotIn("|", raw.replace(r"\|", ""))


class CheckModeTest(unittest.TestCase):
    def test_check_passes_when_in_sync(self):
        result = run_script("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("match", result.stdout)

    def test_check_detects_drift(self):
        original = SKILL.read_text(encoding="utf-8")
        try:
            SKILL.write_text(original.replace("`bsk status`", "`bsk status` (tampered)"), encoding="utf-8", newline="")
            result = run_script("--check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("out of date", result.stderr)
        finally:
            SKILL.write_text(original, encoding="utf-8", newline="")
        self.assertEqual(run_script("--check").returncode, 0)


class MarkerTest(unittest.TestCase):
    def test_markers_exist_and_are_paired(self):
        for path in (SKILL, PROTOCOL):
            text = path.read_text(encoding="utf-8")
            begins = [l for l in text.splitlines() if gen.BEGIN in l]
            ends = [l for l in text.splitlines() if gen.END in l]
            self.assertEqual(len(begins), len(ends), f"{path.name}: markers unbalanced")
            for line in begins + ends:
                block_id = line.split("GENERATED:")[1].split("-->")[0].split("—")[0].strip()
                self.assertIn(block_id, gen.BLOCKS, f"{path.name}: unknown block {block_id!r}")


if __name__ == "__main__":
    unittest.main()
