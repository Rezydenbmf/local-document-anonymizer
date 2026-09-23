"""Regression test for a real user report: opening Settings after being
in the comparison window took a visible 3-5s. Root cause:
SettingsDialog.__init__ called ocr.list_installed_languages() fresh on
every single open - a Tesseract subprocess call - even though the
startup environment check already pays that exact cost once in the
background. Fixed with a lazy cache on the app object, refreshed for
real only after a language pack install actually changes what's
installed.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


class SettingsDialogOcrLanguageCacheTests(unittest.TestCase):
    _root = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._root = ctk.CTk()
        cls._root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._root.destroy()

    def test_second_dialog_open_reuses_the_first_ones_language_lookup(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)

            with patch(
                "gui_settings_dialog.list_installed_languages",
                return_value=["pol", "eng"],
            ) as mocked:
                first = SettingsDialog(app)
                second = SettingsDialog(app)

        mocked.assert_called_once()
        self.assertEqual(first.installed_ocr_languages, ["pol", "eng"])
        self.assertEqual(second.installed_ocr_languages, ["pol", "eng"])
        self.assertEqual(app._installed_ocr_languages_cache, ["pol", "eng"])

    def test_a_fresh_app_with_no_cache_computes_it_once(self) -> None:
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)
            self.assertIsNone(app._installed_ocr_languages_cache)

            with patch(
                "gui_settings_dialog.list_installed_languages",
                return_value=["pol"],
            ) as mocked:
                SettingsDialog(app)

        mocked.assert_called_once()
        self.assertEqual(app._installed_ocr_languages_cache, ["pol"])

    def test_language_install_refreshes_the_cache_not_just_the_dialog(self) -> None:
        """The cache must reflect a real install, not stay stuck on the
        pre-install snapshot for every later Settings open."""
        with workspace_temp_dir() as temp_dir:
            config_path = Path(temp_dir) / "magic_pen_interaction.json"
            app = FakeApp(self._root, config_path)

            with patch(
                "gui_settings_dialog.list_installed_languages",
                return_value=["eng"],
            ):
                dialog = SettingsDialog(app)

            with patch(
                "gui_settings_dialog.list_installed_languages",
                return_value=["eng", "pol"],
            ):
                dialog._on_ocr_language_install_done(True, "")

        self.assertEqual(dialog.installed_ocr_languages, ["eng", "pol"])
        self.assertEqual(app._installed_ocr_languages_cache, ["eng", "pol"])


if __name__ == "__main__":
    unittest.main()
