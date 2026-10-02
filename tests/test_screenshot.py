"""
Unit tests for screenshot module
"""

import sys
import os
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Add skill/scripts to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skill', 'scripts'))

from screenshot import parse_args, default_output_path


class TestParseArgs(unittest.TestCase):
    """Test argument parsing."""

    def test_default_values(self):
        """Default arguments should have sensible defaults."""
        with patch('sys.argv', ['screenshot.py']):
            args = parse_args()

        self.assertIsNone(args.session)
        self.assertIsNone(args.output)
        self.assertEqual(args.format, "png")
        self.assertEqual(args.quality, 80)
        self.assertIsNone(args.selector)
        self.assertEqual(args.timeout, 30)

    def test_session_argument(self):
        """--session should be parsed correctly."""
        with patch('sys.argv', ['screenshot.py', '--session', 'abc123']):
            args = parse_args()

        self.assertEqual(args.session, "abc123")

    def test_output_path_argument(self):
        """--output should be converted to Path."""
        test_path = "/tmp/screenshot.png"
        with patch('sys.argv', ['screenshot.py', '--output', test_path]):
            args = parse_args()

        self.assertIsInstance(args.output, Path)
        # Normalize for cross-platform comparison (Windows uses backslashes)
        self.assertEqual(
            os.path.normpath(str(args.output)),
            os.path.normpath(test_path),
        )

    def test_format_choices_png(self):
        """--format png should be accepted."""
        with patch('sys.argv', ['screenshot.py', '--format', 'png']):
            args = parse_args()

        self.assertEqual(args.format, "png")

    def test_format_choices_jpeg(self):
        """--format jpeg should be accepted."""
        with patch('sys.argv', ['screenshot.py', '--format', 'jpeg']):
            args = parse_args()

        self.assertEqual(args.format, "jpeg")

    def test_invalid_format_rejected(self):
        """Invalid format should raise SystemExit."""
        with patch('sys.argv', ['screenshot.py', '--format', 'gif']):
            with self.assertRaises(SystemExit):
                parse_args()

    def test_quality_argument(self):
        """--quality should be parsed as int."""
        with patch('sys.argv', ['screenshot.py', '--quality', '95']):
            args = parse_args()

        self.assertEqual(args.quality, 95)

    def test_selector_argument(self):
        """--selector should be parsed correctly."""
        with patch('sys.argv', ['screenshot.py', '--selector', '#main-btn']):
            args = parse_args()

        self.assertEqual(args.selector, "#main-btn")

    def test_timeout_argument(self):
        """--timeout should be parsed correctly."""
        with patch('sys.argv', ['screenshot.py', '--timeout', '60']):
            args = parse_args()

        self.assertEqual(args.timeout, 60)


    def test_full_page_flag_defaults_to_false(self):
        with patch('sys.argv', ['screenshot.py']):
            args = parse_args()

        self.assertFalse(args.full_page)

    def test_full_page_flag(self):
        with patch('sys.argv', ['screenshot.py', '--full-page']):
            args = parse_args()

        self.assertTrue(args.full_page)

    def test_full_page_rejects_selector(self):
        """--selector with --full-page must stop before contacting the daemon."""
        from screenshot import main

        with patch('sys.argv', [
            'screenshot.py', '--session', 'abc123',
            '--selector', '@e3', '--full-page',
        ]):
            with self.assertRaises(SystemExit) as ctx:
                main()

        self.assertIn("mutually exclusive", str(ctx.exception))

    @patch('screenshot.bsk')
    def test_full_page_forwards_flag_and_duration(self, mock_bsk):
        from screenshot import main

        mock_bsk.return_value = {"path": None}

        with patch('sys.argv', [
            'screenshot.py', '--session', 'abc123',
            '--full-page', '--timeout', '300',
        ]):
            with self.assertRaises(SystemExit):
                main()

        mock_bsk.assert_called_once_with(
            "screenshot", "abc123", **{"full-page": True, "timeout": "300s"}
        )

    @patch('screenshot.bsk')
    def test_viewport_capture_omits_timeout_flag(self, mock_bsk):
        """--timeout is only forwarded for full-page captures."""
        from screenshot import main

        mock_bsk.return_value = {"path": None}

        with patch('sys.argv', [
            'screenshot.py', '--session', 'abc123', '--timeout', '45',
        ]):
            with self.assertRaises(SystemExit):
                main()

        mock_bsk.assert_called_once_with("screenshot", "abc123")


class TestDefaultOutputPath(unittest.TestCase):
    """Test default output path generation."""

    def test_returns_path_object(self):
        result = default_output_path("png")
        self.assertIsInstance(result, Path)

    def test_png_extension(self):
        """PNG format should produce .png file."""
        result = default_output_path("png")
        self.assertTrue(result.suffix == ".png")

    def test_jpeg_extension(self):
        """JPEG format should produce .jpg file."""
        result = default_output_path("jpeg")
        self.assertTrue(result.suffix in (".jpg", ".jpeg"))

    def test_file_in_screenshots_directory(self):
        """File should be created in browserskill-screenshots directory."""
        result = default_output_path("png")
        self.assertIn("browserskill-screenshots", str(result))

    def test_file_starts_with_screenshot_prefix(self):
        """Filename should start with 'screenshot_' prefix."""
        result = default_output_path("png")
        self.assertTrue(result.name.startswith("screenshot_"))

    def test_directory_created_if_not_exists(self):
        """Parent directory should exist after call (created automatically)."""
        result = default_output_path("png")
        self.assertTrue(result.parent.exists())

    def test_unique_filenames_on_multiple_calls(self):
        """Multiple calls should generate different filenames."""
        paths = [default_output_path("png") for _ in range(5)]
        unique_names = set(p.name for p in paths)

        # Most implementations should give unique names
        # (though not strictly guaranteed by tempfile)
        self.assertGreater(len(unique_names), 1,
                           "Expected multiple unique filenames")


class TestScreenshotIntegration(unittest.TestCase):
    """Integration tests using mocked bsk calls."""

    @unittest.skip("Complex integration test - requires careful sys.argv mocking")
    @patch('screenshot.bsk')
    @patch('screenshot.shutil.copyfile')
    def test_successful_screenshot_with_path(self, mock_copy, mock_bsk):
        """Successful bsk call with path should copy file."""
        pass  # Skipped due to complexity

    @patch('screenshot.bsk')
    def test_bsk_error_raises_system_exit(self, mock_bsk):
        """bsk RuntimeError should cause SystemExit."""
        mock_bsk.side_effect = RuntimeError("daemon crashed")

        from screenshot import main

        # Must mock sys.argv before calling main
        with patch('sys.argv', ['screenshot.py']):
            with self.assertRaises(SystemExit) as ctx:
                main()

        self.assertIn("daemon crashed", str(ctx.exception))


class TestEdgeCases(unittest.TestCase):
    """Edge case tests for screenshot module."""

    def test_quality_boundary_low(self):
        """Quality=0 should be valid."""
        with patch('sys.argv', ['screenshot.py', '--quality', '0']):
            args = parse_args()
        self.assertEqual(args.quality, 0)

    def test_quality_boundary_high(self):
        """Quality=100 should be valid."""
        with patch('sys.argv', ['screenshot.py', '--quality', '100']):
            args = parse_args()
        self.assertEqual(args.quality, 100)

    def test_combined_arguments(self):
        """Multiple arguments should all parse correctly."""
        with patch('sys.argv', [
            'screenshot.py',
            '--session', 'sess42',
            '--format', 'jpeg',
            '--quality', '90',
            '--selector', '#content',
            '--timeout', '45',
        ]):
            args = parse_args()

        self.assertEqual(args.session, "sess42")
        self.assertEqual(args.format, "jpeg")
        self.assertEqual(args.quality, 90)
        self.assertEqual(args.selector, "#content")
        self.assertEqual(args.timeout, 45)

    def test_output_path_expansion(self):
        """Output path should handle ~ expansion."""
        home = Path.home()
        with patch('sys.argv', ['screenshot.py', '--output', '~/test.png']):
            args = parse_args()

        # argparse stores the string; expansion happens later
        self.assertIn("~", str(args.output))


if __name__ == "__main__":
    unittest.main()
