"""Tests for the "Tryb interakcji magic pena" section of the Settings
dialog (Etap 3 - see docs/PROJECT_STATE.md): the mode radio buttons, the
custom-mode per-button dropdowns and their swap-to-stay-valid behavior,
and persisting the choice back onto the app object and to disk. Builds a
real SettingsDialog against a hidden root - the widget tree itself is
part of what needs verifying, since nothing else in this suite ever
constructs one.
"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import customtkinter as ctk

from gui_helpers import (
    MAGIC_PEN_BUILTIN_BINDINGS,
    MAGIC_PEN_MODE_CLASSIC,
    MAGIC_PEN_MODE_CUSTOM,
    MAGIC_PEN_MODE_DEFAULT,
    is_valid_magic_pen_bindings,
    load_magic_pen_interaction_config,
)
from gui_settings_dialog import SettingsDialog


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class FakeApp:
    def __init__(self, root, config_path: Path):
        self.root = root
        self.use_ner = True
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


class SettingsDialogMagicPenModeTests(unittest.TestCase):
    _root = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._root = ctk.CTk()
        cls._root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._root.destroy()

    @staticmethod
    def _is_packed(widget) -> bool:
        return widget.winfo_manager() == "pack"

    def test_custom_bindings_section_starts_hidden_for_builtin_modes(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            dialog = SettingsDialog(app)

            self.assertFalse(self._is_packed(dialog._custom_bindings_frame))

    def test_selecting_custom_mode_reveals_the_bindings_section(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            dialog = SettingsDialog(app)

            dialog.magic_pen_mode_var.set(MAGIC_PEN_MODE_CUSTOM)
            dialog._on_magic_pen_mode_changed()
            self._root.update_idletasks()

            self.assertTrue(self._is_packed(dialog._custom_bindings_frame))

    def test_assigning_a_taken_action_swaps_the_two_buttons(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            dialog = SettingsDialog(app)
            before = dict(dialog._custom_bindings)

            dialog._on_custom_binding_changed("left", before["right"])

            self.assertEqual(dialog._custom_bindings["left"], before["right"])
            self.assertEqual(dialog._custom_bindings["right"], before["left"])
            self.assertEqual(dialog._custom_bindings["middle"], before["middle"])
            self.assertTrue(is_valid_magic_pen_bindings(dialog._custom_bindings))

    def test_swap_updates_the_other_dropdowns_displayed_value(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            dialog = SettingsDialog(app)
            before = dict(dialog._custom_bindings)

            dialog._on_custom_binding_changed("left", before["right"])

            from gui_helpers import MAGIC_PEN_ACTION_LABELS_PL

            self.assertEqual(
                dialog._custom_binding_option_vars["right"].get(),
                MAGIC_PEN_ACTION_LABELS_PL[before["left"]],
            )

    def test_save_and_close_persists_mode_and_bindings_onto_app(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            dialog = SettingsDialog(app)
            dialog.magic_pen_mode_var.set(MAGIC_PEN_MODE_CLASSIC)

            dialog._save_and_close()

            self.assertEqual(app.magic_pen_interaction_mode, MAGIC_PEN_MODE_CLASSIC)

    def test_save_and_close_writes_config_to_disk(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "nested" / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            dialog = SettingsDialog(app)
            dialog.magic_pen_mode_var.set(MAGIC_PEN_MODE_CUSTOM)
            dialog._on_magic_pen_mode_changed()
            dialog._on_custom_binding_changed(
                "left", dialog._custom_bindings["middle"]
            )

            dialog._save_and_close()

            saved = load_magic_pen_interaction_config(config_path)
            self.assertEqual(saved["mode"], MAGIC_PEN_MODE_CUSTOM)
            self.assertEqual(saved["custom_bindings"], app.magic_pen_custom_bindings)


if __name__ == "__main__":
    unittest.main()
