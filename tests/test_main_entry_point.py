"""Tests for the app entry point's crash-logging fallback.

A windowed launch (pythonw.exe, or the packaged --noconsole build) has
no console to print a traceback to - an uncaught exception during
startup would otherwise be completely silent. _log_crash exists so a
real crash leaves a diagnosable trail instead.
"""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import main


class LogCrashTests(unittest.TestCase):
    def test_writes_a_log_file_with_the_exception_traceback(self) -> None:
        with patch.object(Path, "home", return_value=PROJECT_ROOT / "tests" / "_scratch_home"):
            log_path = (
                PROJECT_ROOT / "tests" / "_scratch_home" / ".anonimizer" / "ostatni_blad.log"
            )
            log_path.unlink(missing_ok=True)
            try:
                raise ValueError("synthetic startup failure")
            except ValueError as error:
                main._log_crash(error)

            self.assertTrue(log_path.exists())
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("ValueError", text)
            self.assertIn("synthetic startup failure", text)
            log_path.unlink()
            log_path.parent.rmdir()
            log_path.parent.parent.rmdir()

    def test_never_raises_when_the_log_directory_cannot_be_created(self) -> None:
        with patch.object(Path, "mkdir", side_effect=OSError("read-only filesystem")):
            try:
                raise ValueError("synthetic failure")
            except ValueError as error:
                main._log_crash(error)  # must not raise

    def test_main_reraises_after_logging_a_crash(self) -> None:
        with (
            patch("main.start_gui", side_effect=RuntimeError("boom")),
            patch("main._log_crash") as mock_log,
        ):
            with self.assertRaises(RuntimeError):
                main.main()
            mock_log.assert_called_once()


class SuppressChildConsoleWindowsTests(unittest.TestCase):
    """Regression test for a real user report: 2-3 terminal windows
    flashing a couple seconds after the GUI appears, from background
    startup checks (OCR language list, pip update check, ...) each
    spawning a subprocess with no console-suppression flags of their
    own - including inside the vendored pytesseract library, which
    this app can't edit directly."""

    def setUp(self) -> None:
        self._original_popen_init = subprocess.Popen.__init__

    def tearDown(self) -> None:
        # Never leave the process-wide patch applied past this test -
        # every other test in the same run shares this one process.
        subprocess.Popen.__init__ = self._original_popen_init

    @unittest.skipUnless(sys.platform == "win32", "Windows-only behavior")
    def test_patches_popen_to_inject_create_no_window(self) -> None:
        main._suppress_child_console_windows()

        result = subprocess.run(
            ["cmd", "/c", "echo suppressed"], capture_output=True, check=False
        )

        self.assertEqual(result.stdout.strip(), b"suppressed")
        self.assertIsNot(subprocess.Popen.__init__, self._original_popen_init)

    @unittest.skipUnless(sys.platform == "win32", "Windows-only behavior")
    def test_preserves_a_caller_supplied_creationflags_value(self) -> None:
        # Spy installed *before* _suppress_child_console_windows runs, so
        # it wraps the spy - the spy then sees the already-merged flags
        # the real Popen.__init__ would receive, not the pre-merge value.
        captured: dict[str, int] = {}
        original_init = subprocess.Popen.__init__

        def spy_init(self, *args, **kwargs):
            captured["creationflags"] = kwargs.get("creationflags")
            original_init(self, *args, **kwargs)

        subprocess.Popen.__init__ = spy_init
        main._suppress_child_console_windows()

        subprocess.run(
            ["cmd", "/c", "echo flags"],
            capture_output=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            check=False,
        )

        self.assertEqual(
            captured["creationflags"],
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
        )

    def test_is_a_no_op_off_windows(self) -> None:
        with patch("main.sys.platform", "linux"):
            main._suppress_child_console_windows()

        self.assertIs(subprocess.Popen.__init__, self._original_popen_init)


if __name__ == "__main__":
    unittest.main()
