"""Tests for the startup optional-dependency environment checks."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import environment_check as ec


class CheckNerEnvironmentTests(unittest.TestCase):
    def test_available_when_model_installed(self) -> None:
        with patch("environment_check.check_ner_model_installed", return_value="available"):
            item = ec.check_ner_environment()

        self.assertTrue(item.ok)
        self.assertIsNone(item.install_action)

    def test_model_missing_offers_spacy_download_action(self) -> None:
        with patch(
            "environment_check.check_ner_model_installed", return_value="model_missing"
        ):
            item = ec.check_ner_environment("pl_core_news_sm")

        self.assertFalse(item.ok)
        self.assertEqual(item.install_action, ec.INSTALL_ACTION_SPACY_MODEL)
        self.assertEqual(item.install_target, "pl_core_news_sm")

    def test_dependency_missing_has_no_install_action(self) -> None:
        with patch(
            "environment_check.check_ner_model_installed",
            return_value="dependency_missing",
        ):
            item = ec.check_ner_environment()

        self.assertFalse(item.ok)
        self.assertIsNone(item.install_action)
        self.assertIn("spaCy", item.detail_pl)


class CheckOcrEnvironmentTests(unittest.TestCase):
    def test_available_when_tesseract_found(self) -> None:
        with patch(
            "environment_check.detect_ocr_support", return_value={"status": "available"}
        ):
            item = ec.check_ocr_environment()

        self.assertTrue(item.ok)
        self.assertIsNone(item.install_action)

    def test_engine_not_found_offers_download_url(self) -> None:
        with patch(
            "environment_check.detect_ocr_support",
            return_value={"status": "engine_not_found"},
        ):
            item = ec.check_ocr_environment()

        self.assertFalse(item.ok)
        self.assertEqual(item.install_action, ec.INSTALL_ACTION_OPEN_URL)
        self.assertEqual(item.install_target, ec.TESSERACT_DOWNLOAD_URL)

    def test_dependency_missing_also_offers_download_url(self) -> None:
        with patch(
            "environment_check.detect_ocr_support",
            return_value={"status": "dependency_missing"},
        ):
            item = ec.check_ocr_environment()

        self.assertFalse(item.ok)
        self.assertEqual(item.install_action, ec.INSTALL_ACTION_OPEN_URL)


class CheckLlmEnvironmentTests(unittest.TestCase):
    def test_available_when_ollama_present(self) -> None:
        with patch(
            "environment_check.list_installed_models", return_value=("available", ["llama3"])
        ):
            item = ec.check_llm_environment()

        self.assertTrue(item.ok)

    def test_treated_as_ok_when_ollama_present_but_no_models_pulled(self) -> None:
        # Not "ollama_not_found" - ollama itself is installed, just no model
        # pulled yet; that nuance is handled in Settings, not the startup banner.
        with patch(
            "environment_check.list_installed_models",
            return_value=("no_model_configured", []),
        ):
            item = ec.check_llm_environment()

        self.assertTrue(item.ok)

    def test_ollama_not_found_offers_download_url(self) -> None:
        with patch(
            "environment_check.list_installed_models",
            return_value=("ollama_not_found", []),
        ):
            item = ec.check_llm_environment()

        self.assertFalse(item.ok)
        self.assertEqual(item.install_action, ec.INSTALL_ACTION_OPEN_URL)
        self.assertEqual(item.install_target, ec.OLLAMA_DOWNLOAD_URL)


class CheckEnvironmentTests(unittest.TestCase):
    def test_returns_one_item_per_dependency_in_order(self) -> None:
        with (
            patch("environment_check.check_ner_model_installed", return_value="available"),
            patch(
                "environment_check.detect_ocr_support", return_value={"status": "available"}
            ),
            patch(
                "environment_check.list_installed_models", return_value=("available", [])
            ),
        ):
            items = ec.check_environment()

        self.assertEqual([item.item for item in items], [ec.ENV_ITEM_NER, ec.ENV_ITEM_OCR, ec.ENV_ITEM_LLM])
        self.assertTrue(all(item.ok for item in items))


class InstallNerModelTests(unittest.TestCase):
    def test_reports_success_on_zero_return_code(self) -> None:
        class FakeCompleted:
            returncode = 0
            stdout = ""
            stderr = ""

        with patch("environment_check.subprocess.run", return_value=FakeCompleted()):
            success, message = ec.install_ner_model("pl_core_news_sm")

        self.assertTrue(success)
        self.assertEqual(message, "")

    def test_reports_failure_with_captured_stderr(self) -> None:
        class FakeCompleted:
            returncode = 1
            stdout = ""
            stderr = "network unreachable"

        with patch("environment_check.subprocess.run", return_value=FakeCompleted()):
            success, message = ec.install_ner_model("pl_core_news_sm")

        self.assertFalse(success)
        self.assertIn("network unreachable", message)

    def test_reports_failure_on_timeout(self) -> None:
        import subprocess

        with patch(
            "environment_check.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="spacy", timeout=1),
        ):
            success, message = ec.install_ner_model("pl_core_news_sm", timeout_seconds=1)

        self.assertFalse(success)
        self.assertTrue(message)


if __name__ == "__main__":
    unittest.main()
