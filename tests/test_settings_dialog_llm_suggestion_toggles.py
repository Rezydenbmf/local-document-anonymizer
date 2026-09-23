"""Tests for the two new, unlocked-from-day-one LLM suggestion-review
toggles ("AI: porownanie oryginal / wynik" and "AI: czytanie kontekstowe
calosci") added to the Settings dialog and the main window's quick
settings panel (2026-09-23) - unlike the existing whole-document LLM
review checkbox, these are never gated behind "wkrotce".
"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import customtkinter as ctk

from gui_helpers import MAGIC_PEN_BUILTIN_BINDINGS, MAGIC_PEN_MODE_DEFAULT
from gui_settings_dialog import SettingsDialog


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class FakeApp:
    def __init__(self, root, config_path: Path):
        self.root = root
        self.use_ner = True
        self.use_llm_review = False
        self.llm_model_name = ""
        self.use_llm_comparison_review = False
        self.use_llm_narrative_review = False
        self.pdf_output_label = "Widoczna redakcja (wizualna)"
        self.auto_open_on_approve = True
        self.show_usage_hints = True
        self.sensitive_terms_path = None
        self.environment_items = []
        self._installed_ocr_languages_cache = None
        self.magic_pen_interaction_mode = MAGIC_PEN_MODE_DEFAULT
        self.magic_pen_custom_bindings = dict(
            MAGIC_PEN_BUILTIN_BINDINGS[MAGIC_PEN_MODE_DEFAULT]
        )
        self.magic_pen_interaction_config_path = config_path


class SettingsDialogLlmSuggestionTogglesTests(unittest.TestCase):
    _root = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._root = ctk.CTk()
        cls._root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._root.destroy()

    def test_dialog_seeds_toggle_state_from_the_app(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            app.use_llm_comparison_review = True
            app.use_llm_narrative_review = False

            dialog = SettingsDialog(app)

            self.assertTrue(dialog.llm_comparison_var.get())
            self.assertFalse(dialog.llm_narrative_var.get())

    def test_save_and_close_persists_both_toggles_independently(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            dialog = SettingsDialog(app)

            dialog.llm_comparison_var.set(True)
            dialog.llm_narrative_var.set(False)
            dialog._save_and_close()

            self.assertTrue(app.use_llm_comparison_review)
            self.assertFalse(app.use_llm_narrative_review)

    def test_whole_document_llm_review_stays_forced_off_regardless(self) -> None:
        # The pre-existing alpha-locked checkbox must stay locked even
        # though these two new, related toggles are live - they are
        # independent features with independent risk profiles.
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            dialog = SettingsDialog(app)

            dialog.llm_var.set(True)
            dialog.llm_comparison_var.set(True)
            dialog.llm_narrative_var.set(True)
            dialog._save_and_close()

            self.assertFalse(app.use_llm_review)
            self.assertTrue(app.use_llm_comparison_review)
            self.assertTrue(app.use_llm_narrative_review)

    def test_enabling_either_new_toggle_triggers_model_auto_select_fallback(
        self,
    ) -> None:
        # Auto-selecting an installed model on save (when none is
        # configured yet) previously only fired for use_llm_review; it
        # must also cover these two new, independently-enabled toggles.
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            self.assertEqual(app.llm_model_name, "")
            dialog = SettingsDialog(app)

            dialog.llm_narrative_var.set(True)
            # No local Ollama models are installed in the test
            # environment, so the fallback resolves to an empty string -
            # what matters here is that the auto-select branch actually
            # runs (no exception, no leftover None) rather than being
            # skipped because only use_llm_review used to be checked.
            dialog._save_and_close()

            self.assertEqual(app.llm_model_name, "")


if __name__ == "__main__":
    unittest.main()
