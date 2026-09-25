"""AI toggled on from the home screen must not run without a model
(2026-09-25 real run: the sidecar said "no_model_configured" - only
Settings > Zapisz used to pick a model)."""

import sys
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import gui_app
from gui_app import AnonymizerApp


def _app(model: str = "", comparison: bool = True, narrative: bool = False):
    app = AnonymizerApp.__new__(AnonymizerApp)
    app.root = None
    app.llm_model_name = model
    app.use_llm_comparison_review = comparison
    app.use_llm_narrative_review = narrative
    return app


class EnsureLlmModelForRunTests(unittest.TestCase):
    def test_ai_off_needs_nothing(self) -> None:
        app = _app(comparison=False)
        with mock.patch.object(gui_app, "list_installed_models") as listing:
            self.assertTrue(app._ensure_llm_model_for_run())
        listing.assert_not_called()
        self.assertEqual(app.llm_model_name, "")

    def test_chosen_model_is_kept(self) -> None:
        app = _app(model="gemma3:4b")
        with mock.patch.object(gui_app, "list_installed_models") as listing:
            self.assertTrue(app._ensure_llm_model_for_run())
        listing.assert_not_called()
        self.assertEqual(app.llm_model_name, "gemma3:4b")

    def test_falls_back_to_first_installed_model(self) -> None:
        app = _app(narrative=True, comparison=False)
        with mock.patch.object(
            gui_app,
            "list_installed_models",
            return_value=("available", ["gemma3:4b", "bielik"]),
        ):
            self.assertTrue(app._ensure_llm_model_for_run())
        self.assertEqual(app.llm_model_name, "gemma3:4b")

    def test_no_model_asks_and_respects_the_answer(self) -> None:
        for answer in (True, False):
            app = _app()
            with mock.patch.object(
                gui_app, "list_installed_models", return_value=("available", [])
            ), mock.patch.object(
                gui_app.messagebox, "askyesno", return_value=answer
            ) as ask:
                self.assertIs(app._ensure_llm_model_for_run(), answer)
            ask.assert_called_once()
            self.assertEqual(app.llm_model_name, "")


if __name__ == "__main__":
    unittest.main()
