"""Settings -> home screen quick-settings sync (2026-09-25 user report:
turning the AI switches on in Settings and saving left the home screen's
"AI: ..." checkboxes unticked)."""

import sys
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import gui_app
from gui_app import AnonymizerApp


class QuickSettingsSyncTests(unittest.TestCase):
    _root = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._root = tk.Tk()
        cls._root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._root.destroy()

    def _app(self) -> AnonymizerApp:
        app = AnonymizerApp.__new__(AnonymizerApp)
        app.use_ner = True
        app.use_llm_comparison_review = False
        app.use_llm_narrative_review = False
        app._quick_ner_var = tk.BooleanVar(master=self._root, value=True)
        app._quick_llm_comparison_var = tk.BooleanVar(master=self._root, value=False)
        app._quick_llm_narrative_var = tk.BooleanVar(master=self._root, value=False)
        return app

    def test_sync_pushes_saved_state_into_quick_checkboxes(self) -> None:
        app = self._app()
        app.use_ner = False
        app.use_llm_comparison_review = True
        app.use_llm_narrative_review = True

        app._sync_quick_settings_from_state()

        self.assertFalse(app._quick_ner_var.get())
        self.assertTrue(app._quick_llm_comparison_var.get())
        self.assertTrue(app._quick_llm_narrative_var.get())

    def test_sync_before_quick_panel_is_built_is_a_no_op(self) -> None:
        app = self._app()
        app._quick_ner_var = None
        app._quick_llm_comparison_var = None
        app._quick_llm_narrative_var = None

        app._sync_quick_settings_from_state()  # must not raise

    def test_saving_settings_syncs_and_still_runs_callers_callback(self) -> None:
        app = self._app()
        caller_callback = mock.Mock()
        with mock.patch.object(gui_app, "SettingsDialog") as dialog_cls:
            app.open_settings(on_saved=caller_callback)
        on_saved = dialog_cls.call_args.kwargs["on_saved"]

        # What SettingsDialog._save_and_close does before calling on_saved.
        app.use_llm_comparison_review = True
        on_saved()

        self.assertTrue(app._quick_llm_comparison_var.get())
        caller_callback.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
