"""Tests for the Stage 1 plain text anonymizer."""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import SUPPORTED_LABELS, anonymize_text


class AnonymizerEngineTests(unittest.TestCase):
    def test_replaces_pesel(self) -> None:
        text = "Synthetic PESEL: 00000000000."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Synthetic PESEL: [PESEL].")
        self.assertEqual(report, {"PESEL": 1})

    def test_replaces_email(self) -> None:
        text = "Contact: tester@example.test."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Contact: [EMAIL].")
        self.assertEqual(report, {"EMAIL": 1})

    def test_replaces_telefon(self) -> None:
        text = "Phone: +48 123 456 789."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Phone: [TELEFON].")
        self.assertEqual(report, {"TELEFON": 1})

    def test_replaces_data(self) -> None:
        text = "Date: 2026-06-01."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Date: [DATA].")
        self.assertEqual(report, {"DATA": 1})

    def test_replaces_conservative_person_name_typo_pattern(self) -> None:
        text = "Reviewer Jan-Kowalski Kowalski signed."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Reviewer [PERSON_NAME_TYPO] signed.")
        self.assertEqual(report, {"PERSON_NAME_TYPO": 1})

    def test_replaces_multiple_categories_in_one_text(self) -> None:
        text = (
            "Email tester@example.test on 2026-06-01. "
            "PESEL: 00000000000. Tel: 123-456-789."
        )

        anonymized, report = anonymize_text(text)

        self.assertEqual(
            anonymized,
            "Email [EMAIL] on [DATA]. PESEL: [PESEL]. Tel: [TELEFON].",
        )
        self.assertEqual(
            report,
            {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1},
        )

    def test_counts_multiple_occurrences_of_same_category(self) -> None:
        text = "Emails: first@example.test and second@example.test."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, "Emails: [EMAIL] and [EMAIL].")
        self.assertEqual(report, {"EMAIL": 2})

    def test_no_match_returns_unchanged_text_and_empty_report(self) -> None:
        text = "Plain synthetic note without supported identifiers."

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_does_not_replace_values_embedded_in_tokens(self) -> None:
        text = "token00000000000x ref2026-06-01x abc123-456-789z"

        anonymized, report = anonymize_text(text)

        self.assertEqual(anonymized, text)
        self.assertEqual(report, {})

    def test_report_does_not_contain_source_values(self) -> None:
        source_values = {
            "safe@example.test",
            "00000000000",
            "+48 123 456 789",
            "2026-06-01",
        }
        text = "safe@example.test 00000000000 +48 123 456 789 2026-06-01"

        _, report = anonymize_text(text)

        report_as_text = repr(report)
        for source_value in source_values:
            self.assertNotIn(source_value, report_as_text)
        self.assertEqual(report, {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1})

    def test_supported_labels_are_limited_to_current_regex_categories(self) -> None:
        self.assertEqual(
            SUPPORTED_LABELS,
            ("PESEL", "EMAIL", "TELEFON", "DATA", "PERSON_NAME_TYPO"),
        )


if __name__ == "__main__":
    unittest.main()
