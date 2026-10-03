"""Tests for scripts/switch_extension.py (pure logic, no real Edge profiles)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import switch_extension as sw  # noqa: E402


class PathNormalisationTest(unittest.TestCase):
    def test_treats_separator_and_case_differences_as_equal(self):
        self.assertEqual(
            sw.norm(r"D:\916938\browserskill-new\apps\extension\dist\chrome-mv3"),
            sw.norm("D:/916938/BrowserSkill-New/apps/extension/dist/chrome-mv3"),
        )


class ProfileDiscoveryTest(unittest.TestCase):
    def test_orders_default_first_then_numbered_profiles(self):
        root = Path(__file__).resolve().parent / "_fx_profiles"
        for name in ("Default", "Profile 2", "Profile 10", "Profile 1", "Guest Profile", "Extensions"):
            (root / name).mkdir(parents=True, exist_ok=True)
        try:
            self.assertEqual(sw.find_profiles(root), ["Default", "Profile 1", "Profile 2", "Profile 10"])
        finally:
            import shutil

            shutil.rmtree(root, ignore_errors=True)

    def test_missing_user_data_dir_raises(self):
        with self.assertRaises(RuntimeError):
            sw.find_profiles(Path("C:/definitely/not/here"))


class PlanningTest(unittest.TestCase):
    OLD = r"D:\916938\browserskill-new\apps\extension\dist\chrome-mv3"
    NEW = r"D:\916938\zenx-bridge-main\apps\extension\dist\chrome-mv3"
    EXT_ID = "agcgbdanbihfkcdmgegblkioiiepecln"

    def _profile(self, root: Path, path: str | None) -> Path:
        profile = root / "Default"
        profile.mkdir(parents=True, exist_ok=True)
        settings = {}
        if path is not None:
            settings[self.EXT_ID] = {"path": path, "from_webstore": False}
        settings["dmaldhchmoafliphkijbfhaomcgglmgd"] = {"path": r"dmaldhchmoafliphkijbfhaomcgglmgd\3.5.2_0"}
        (profile / "Secure Preferences").write_text(
            __import__("json").dumps({"extensions": {"settings": settings}}), encoding="utf-8"
        )
        return profile

    def test_detects_stale_path_and_ignores_webstore_entries(self):
        root = Path(__file__).resolve().parent / "_fx_plan"
        import shutil

        shutil.rmtree(root, ignore_errors=True)
        try:
            profile = self._profile(root, self.OLD)
            plan = sw.plan_profile(profile, Path(self.OLD), Path(self.NEW))
            self.assertEqual(plan["ids"], [self.EXT_ID])
            self.assertEqual(plan["stale"], [self.EXT_ID])
            self.assertEqual(plan["already"], [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_already_switched_profiles_are_a_no_op(self):
        root = Path(__file__).resolve().parent / "_fx_done"
        import shutil

        shutil.rmtree(root, ignore_errors=True)
        try:
            profile = self._profile(root, self.NEW)
            plan = sw.plan_profile(profile, Path(self.OLD), Path(self.NEW))
            self.assertEqual(plan["stale"], [])
            self.assertEqual(plan["already"], [self.EXT_ID])
            self.assertEqual(sw.apply_profile(plan, Path(self.NEW), backup=False), [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_profile_without_unpacked_entry_is_skipped(self):
        root = Path(__file__).resolve().parent / "_fx_none"
        import shutil

        shutil.rmtree(root, ignore_errors=True)
        try:
            profile = self._profile(root, None)
            plan = sw.plan_profile(profile, Path(self.OLD), Path(self.NEW))
            self.assertIsNone(plan["file"])
            self.assertEqual(plan["ids"], [])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class ValidationTest(unittest.TestCase):
    def test_rejects_directory_without_manifest(self):
        with self.assertRaises(RuntimeError):
            sw.validate_extension_dir(Path(__file__).resolve().parent, "new")


if __name__ == "__main__":
    unittest.main()
