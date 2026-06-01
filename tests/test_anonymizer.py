"""Placeholder tests for the Stage 0 anonymizer module."""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import SUPPORTED_LABELS, AnonymizationResult, anonymize_text


class AnonymizerPlaceholderTests(unittest.TestCase):
    def test_anonymize_text_returns_original_text_for_now(self) -> None:
        sample_text = "Synthetic Person, PESEL 00000000000, email user@example.test"

        result = anonymize_text(sample_text)

        self.assertIsInstance(result, AnonymizationResult)
        self.assertEqual(result.text, sample_text)
        self.assertEqual(result.detected_labels, ())

    def test_supported_labels_are_declared(self) -> None:
        self.assertIn("PESEL", SUPPORTED_LABELS)
        self.assertIn("EMAIL", SUPPORTED_LABELS)
        self.assertIn("IMIE NAZWISKO", SUPPORTED_LABELS)


if __name__ == "__main__":
    unittest.main()
