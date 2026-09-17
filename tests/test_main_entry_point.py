"""Tests for the app entry point's crash-logging fallback.

A windowed launch (pythonw.exe, or the packaged --noconsole build) has
no console to print a traceback to - an uncaught exception during
startup would otherwise be completely silent. _log_crash exists so a
real crash leaves a diagnosable trail instead.
"""

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


if __name__ == "__main__":
    unittest.main()
