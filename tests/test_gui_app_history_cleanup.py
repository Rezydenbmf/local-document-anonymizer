"""Regression test for a real bug reported live: a history entry whose
folder had been deleted outside the app entirely (not by "Wyczysc
historie", e.g. via Explorer) showed "folder nie istnieje" forever and
never got dropped from the Historia list - clean_history()'s old
folder-filtering only ever considered folders that still exist on disk,
so a fully-missing one never had a chance to be pruned. Exercises the
extracted _forget_missing_history_entries helper directly (bare instance,
real temp file for the history config) rather than the full
clean_history() flow, which needs a real Tk root and messagebox dialogs.
"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gui_app import AnonymizerApp
from gui_helpers import load_recent_folders, save_recent_folders


class ForgetMissingHistoryEntriesTests(unittest.TestCase):
    def _build_app(self, temp_dir, entries):
        app = AnonymizerApp.__new__(AnonymizerApp)
        app.history_config_path = Path(temp_dir) / "recent_folders.json"
        app.recent_folders = list(entries)
        save_recent_folders(app.history_config_path, app.recent_folders)
        return app

    def test_drops_only_entries_in_stale_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gone = str(Path(temp_dir) / "gone")
            still_here = str(Path(temp_dir) / "still_here")
            Path(still_here).mkdir()
            app = self._build_app(
                temp_dir,
                [
                    {"path": gone, "last_used": "2026-09-08"},
                    {"path": still_here, "last_used": "2026-09-17"},
                ],
            )

            changed = app._forget_missing_history_entries({gone})

            self.assertTrue(changed)
            self.assertEqual(app.recent_folders, [{"path": still_here, "last_used": "2026-09-17"}])
            # Persisted, not just held in memory - a later screen refresh
            # reloads from this file (see show_history_screen).
            self.assertEqual(
                load_recent_folders(app.history_config_path), app.recent_folders
            )

    def test_empty_stale_paths_changes_nothing_and_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            entry = {"path": str(Path(temp_dir) / "still_here"), "last_used": "x"}
            app = self._build_app(temp_dir, [entry])
            before_mtime = app.history_config_path.stat().st_mtime_ns

            changed = app._forget_missing_history_entries(set())

            self.assertFalse(changed)
            self.assertEqual(app.recent_folders, [entry])
            self.assertEqual(app.history_config_path.stat().st_mtime_ns, before_mtime)

    def test_a_path_not_present_in_recent_folders_is_a_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            entry = {"path": str(Path(temp_dir) / "still_here"), "last_used": "x"}
            app = self._build_app(temp_dir, [entry])

            changed = app._forget_missing_history_entries({str(Path(temp_dir) / "unrelated")})

            self.assertFalse(changed)
            self.assertEqual(app.recent_folders, [entry])


if __name__ == "__main__":
    unittest.main()
